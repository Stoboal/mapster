from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    Feedback,
    GameResult,
    Location,
    Rating,
    get_coordinates,
    get_country,
)
from users.models import TelegramUser


class GeneralTestMixin:
    @classmethod
    def setUpTestData(cls):
        cls.street_url = 'https://maps.app.goo.gl/7Q9BX6YNMA7juebS6'
        cls.lat = 51.0894236
        cls.lng = -115.3452451
        cls.country = 'Canada'
        cls.duration = 1
        cls.error = 0.1
        cls.score = 329.49
        cls.moves = 1

    def setUp(self):
        # mocks
        self.patcher_coordinates = patch('core.models.get_coordinates')
        self.patcher_country = patch('core.models.get_country')

        self.mock_get_coordinates = self.patcher_coordinates.start()
        self.mock_get_country = self.patcher_country.start()

        self.mock_get_coordinates.return_value = (self.lat, self.lng)
        self.mock_get_country.return_value = self.country

        # creating objects
        self.user = TelegramUser.objects.create(
            telegram_id = '123456789',
            chat_id = 123456789
        )
        self.location = Location.objects.create(
            street_view_url = self.street_url,
            complexity='easy'
        )

    def tearDown(self):
        self.patcher_coordinates.stop()
        self.patcher_country.stop()

    @patch('core.models.GameResult.calculate_distance_error')
    def create_game_result(self, mock_calculate_distance_error):
        mock_calculate_distance_error.return_value = 0.1
        game_result = GameResult.objects.create(
            user=self.user,
            location=self.location,
            guessed_lat=50.0,
            guessed_lng=-115.0,
            duration=1,
        )
        return game_result

# Models tests

class LocationModelTest(GeneralTestMixin, TestCase):
    def test_get_coordinates_good_data(self):
        self.patcher_coordinates.stop()
        self.patcher_country.stop()

        coordinates = get_coordinates(self.street_url)
        self.assertEqual((self.lat, self.lng), coordinates)

        self.patcher_coordinates.start()
        self.patcher_country.start()

    def test_get_coordinates_invalid_data(self):
        self.patcher_coordinates.stop()

        coordinates = get_coordinates('wrong_url')
        self.assertIsNone(coordinates)

        self.patcher_coordinates.start()

    def test_get_country_good_data(self):
        self.patcher_country.stop()

        country = get_country(self.lat, self.lng)
        self.assertEqual(country, self.country)

        self.patcher_country.start()

    def test_get_country_invalid_data(self):
        self.patcher_country.stop()

        with self.assertRaisesMessage(ValueError, 'Country not found'):
            get_country(0, 0)

        self.patcher_country.start()

    def test_location_creation(self):
        self.mock_get_coordinates.assert_called_once_with(self.street_url)
        self.mock_get_country.assert_called_once_with(self.lat, self.lng)

        self.assertEqual(self.location.street_view_url, self.street_url)
        self.assertEqual(self.location.lat, self.lat)
        self.assertEqual(self.location.lng, self.lng)
        self.assertEqual(self.location.country, self.country)

    def test_location_recalculate_stats(self):
        self.mock_get_coordinates.return_value = (self.lat, self.lng)
        self.mock_get_country.return_value = self.country

        self.location.recalculate_location_stats(
            duration=1,
            error=1.0,
            score=1.0,
            moves=1
        )

        self.assertEqual(self.location.total_guesses, 1)
        self.assertEqual(self.location.total_time, 1)
        self.assertEqual(self.location.total_errors, 1)
        self.assertEqual(self.location.total_moves, 1)
        self.assertEqual(self.location.total_score, 1.0)

    def test_location_recalculate_stats_with_invalid_data(self):
        with self.assertRaisesMessage(ValueError, 'Data types are not as expected'):
            self.location.recalculate_location_stats(1,1,'a',1)

        with self.assertRaisesMessage(ValueError, 'Some of the values are not positive or zero'):
            self.location.recalculate_location_stats(0,0.0,0.0,0)


class GameResultModelTest(GeneralTestMixin, TestCase):
    def test_game_result_creation(self):
        game_result = self.create_game_result()

        self.assertEqual(game_result.user, self.user)
        self.assertEqual(game_result.location, self.location)
        self.assertEqual(game_result.distance_error, 0.1)
        self.assertIsNotNone(game_result.score)

        # recalculation for user
        self.assertEqual(self.user.games, 1)
        self.assertEqual(self.user.total_time, 1)
        self.assertEqual(self.user.total_errors, 0.1)
        self.assertEqual(self.user.total_score, 329.49)

        # recalculation for location
        self.assertEqual(self.location.total_score, 329.49)
        self.assertEqual(self.location.total_guesses, 1)
        self.assertEqual(self.location.total_time, 1)
        self.assertEqual(self.location.total_errors, 0.1)

    def test_game_result_deletion(self):
        game_result = self.create_game_result()
        game_result.delete()

        # recalculation for user
        self.assertEqual(self.user.games, 0)
        self.assertEqual(self.user.total_time, 0)
        self.assertEqual(self.user.total_errors, 0.0)
        self.assertEqual(self.user.total_score, 0.0)

        # recalculation for location
        self.assertEqual(self.location.total_score, 0.0)
        self.assertEqual(self.location.total_guesses, 0)
        self.assertEqual(self.location.total_time, 0)
        self.assertEqual(self.location.total_errors, 0.0)


class RatingModelTest(GeneralTestMixin, TestCase):
    def create_rating_object(self):
        self.create_game_result()
        self.user.games = 5
        self.user.save()

        rating = Rating.objects.create(data=[])
        return rating

    def test_rating_creation_and_updating(self):
        rating = self.create_rating_object()

        with patch('core.models.now') as mock_now:
            mock_now.return_value = self.location.created_at + timedelta(seconds=30)

            rating.update_rating()
            rating.refresh_from_db()

            self.assertEqual(len(rating.data), 1)
            self.assertEqual(rating.data[0]['username'], self.user.username)
            self.assertEqual(rating.data[0]['games'], self.user.games)
            self.assertEqual(rating.data[0]['score'], self.user.total_score)
            self.assertEqual(rating.data[0]['score_for_game'], self.user.total_score / self.user.games)


class FeedbackModelTest(GeneralTestMixin, TestCase):
    def create_feedback(self, answered=False, with_answer=True):
        feedback = Feedback.objects.create(
            user=self.user,
            feedback_text='Test feedback',
            answered = answered
        )

        if with_answer:
            feedback.answer = 'Test answer'
            feedback.save()

        return feedback

    @patch('telebot.TeleBot')
    @patch('os.environ.get')
    def test_send_answer_success(self, mock_env_get, mock_telebot):
        mock_env_get.return_value = 'test_token'
        mock_bot_instance = Mock()
        mock_telebot.return_value = mock_bot_instance

        feedback = self.create_feedback(answered=True, with_answer=True)
        feedback.send_answer()

        mock_env_get.assert_called_once_with("TELEGRAM_TOKEN")
        mock_telebot.assert_called_once_with('test_token')
        mock_bot_instance.send_message.assert_called_once_with(
            chat_id=self.user.chat_id,
            text=f'Answer for your feedback:\n\n{feedback.answer}\n\nThank you for your opinion!'
        )

        feedback.refresh_from_db()
        self.assertIsNotNone(feedback.sent_at)

    @patch('telebot.TeleBot')
    @patch('os.environ.get')
    def test_send_answer_no_token(self, mock_env_get, mock_telebot):
        mock_env_get.return_value = None

        feedback = self.create_feedback(answered=True, with_answer=True)
        feedback.send_answer()

        with self.assertLogs('core.models', level='ERROR') as log:
            feedback.send_answer()

        self.assertIn('TELEGRAM_TOKEN environment variable not set', log.output[0])
        mock_telebot.assert_not_called()

    @patch('telebot.TeleBot')
    @patch('os.environ.get')
    def test_send_answer_telegram_error(self, mock_env_get, mock_telebot):
        mock_env_get.return_value = 'test_token'
        mock_bot_instance = Mock()
        mock_bot_instance.send_message.side_effect = Exception('Telegram API Error')
        mock_telebot.return_value = mock_bot_instance

        feedback = self.create_feedback(answered=True, with_answer=True)
        with self.assertLogs('core.models', level='ERROR') as log:
            feedback.send_answer()

        self.assertIn('Error sending answer for Feedback', log.output[0])

        feedback.refresh_from_db()
        self.assertIsNone(feedback.sent_at)

    def test_send_answer_not_answered(self):
        feedback = self.create_feedback(answered=False, with_answer=False)

        with self.assertLogs('core.models', level='WARNING') as log:
            feedback.send_answer()

        self.assertIn('Cannot send answer for Feedback', log.output[0])

    def test_send_answer_no_answer_text(self):
        feedback = self.create_feedback(answered=True, with_answer=False)

        with self.assertLogs('core.models', level='WARNING') as log:
            feedback.send_answer()

        self.assertIn('Cannot send answer for Feedback', log.output[0])

# API Tests
class GetUserViewTest(GeneralTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('get_user')

    def test_get_user_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_user_authorized(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.user.id)
        self.assertEqual(response.data['username'], self.user.username)


class GetRatingViewTest(GeneralTestMixin, APITestCase):
    def setUp(self):
        super().setUp()

        self.url = reverse('get_rating')
        self.user.games = 10
        self.user.total_score = 100.0
        self.user.save()

    def test_get_rating_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_creating_rating_with_no_data(self):
        self.assertIsNone(Rating.objects.first())

        # Erasing data for existing user
        self.user.games = 0
        self.user.total_score = 0.0
        self.user.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 0)
        self.assertIsNotNone(response.data['updated_at'])

    def test_get_rating(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['username'], self.user.username)
        self.assertEqual(response.data['data'][0]['score'], self.user.total_score)
        self.assertEqual(response.data['data'][0]['score_for_game'], self.user.total_score / self.user.games)

    def test_update_rating_if_no_changes(self):
        """
        Testing rating updating if no changes in data. Rating should not be updated.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)
        rating_old = Rating.objects.first()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with patch('core.models.now') as mock_now:
            mock_now.return_value = rating_old.updated_at + timedelta(seconds=60)
            self.client.get(self.url)
            rating_new = Rating.objects.first()
            self.assertEqual(rating_old, rating_new)

    def test_update_rating_after_changes(self):
        """
        Testing rating updating if changes in data. Rating should be updated.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)
        rating_old = Rating.objects.first()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)

        with patch('core.models.now') as mock_now:
            mock_now.return_value = rating_old.updated_at + timedelta(seconds=60)

            # Creating additional user
            TelegramUser.objects.create(
                telegram_id='987654321',
                chat_id=987654321,
                games=10,
                total_score=100.0
            )
            response = self.client.get(self.url)
            new_rating = Rating.objects.first()

            self.assertNotEqual(rating_old.data, new_rating.data)
            self.assertEqual(len(response.data['data']), 2)


class GetLocationViewTest(GeneralTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('get_location')

        self.location_medium = Location.objects.create(
            street_view_url = self.street_url,
            complexity='medium'
        )
        self.location_hard = Location.objects.create(
            street_view_url = self.street_url,
            complexity='hard'
        )

    def test_get_location_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_location_easy(self):
        """
        Users with games <= 5 must receive only easy locations
        """
        self.user.games = 4
        self.user.save()
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['complexity'], 'easy')
        self.assertEqual(response.data['id'], self.location.id)

    def test_get_location_not_easy(self):
        """
        Users with games > 5 receiving random complexity locations
        """
        self.user.games = 5
        self.user.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        # Receiving easy location
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['complexity'], 'easy')
        self.assertEqual(response.data['id'], self.location.id)
        GameResult.objects.create(
            user=self.user,
            location=self.location,
            guessed_lat=50.0,
            guessed_lng=-115.0,
            duration=1,
        )

        # Receiving random location.
        # In this case location can't be easy because of GameResult was created before with only easy location.
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data['complexity'], 'easy')
        self.assertNotEqual(response.data['id'], self.location.id)

    def test_get_location_no_locations(self):
        """
        In this test user 'playing' all 3 existing locations and getting 404 after attempting to play another one
        """
        self.user.games = 5
        self.user.save()
        self.client.force_authenticate(user=self.user)

        locations = Location.objects.all().count()
        # Calling 3 times for getting results for all 3 locations
        for _i in range(locations):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            location = Location.objects.get(id=response.data['id'])
            GameResult.objects.create(
                user=self.user,
                location=location,
                guessed_lat=50.0,
                guessed_lng=-115.0,
                duration=1,
            )

        # Calling a 4th time for getting 404
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SubmitGuessViewTest(GeneralTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('submit_guess')

    def test_submit_guess_unauthorized(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_guess_authorized(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {
            'location_id': self.location.id,
            'guessed_lat': self.lat - 1.0,
            'guessed_lng': self.lng - 1.0,
            'duration': self.duration,
            'moves_used': self.moves
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        guess = GameResult.objects.first()
        self.assertEqual(guess.user, self.user)
        self.assertEqual(guess.location, self.location)
        self.assertEqual(guess.guessed_lat, self.lat - 1.0)
        self.assertEqual(guess.guessed_lng, self.lng - 1.0)
        self.assertEqual(guess.duration, self.duration)
        self.assertEqual(guess.moves_used, self.moves)
        self.assertIsNotNone(guess.score)

        self.user.refresh_from_db()
        self.assertEqual(self.user.games, 1)
        self.location.refresh_from_db()
        self.assertEqual(self.location.total_guesses, 1)

    def test_submit_guess_invalid_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SendFeedbackAPIView(GeneralTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('send_feedback')

    def test_send_feedback_unauthorized(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_send_feedback(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {
            'feedback_text': 'Test feedback'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Feedback submitted successfully')
        self.assertEqual(Feedback.objects.count(), 1)
        self.assertEqual(Feedback.objects.first().feedback_text, 'Test feedback')
        self.assertEqual(Feedback.objects.first().user, self.user)
        self.assertIsNone(Feedback.objects.first().answer)
        self.assertIsNone(Feedback.objects.first().sent_at)
        self.assertFalse(Feedback.objects.first().answered)

    def test_send_feedback_invalid_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
