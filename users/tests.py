import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from users.models import TelegramUser, DAILY_MOVES_LIMIT
from users.views import check_telegram_auth


class TelegramUserModelTest(TestCase):
    """
    Tests for TelegramUser model
    """
    def setUp(self):
        self.user = TelegramUser.objects.create(
            telegram_id = '123456789',
            username = 'testuser',
            chat_id = '987654321',
        )
        self.duration = 120
        self.error = 5
        self.score = 100
        self.moves = 1


    def test_user_creation(self):
        self.assertEqual(self.user.telegram_id, '123456789')
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.chat_id, '987654321')
        self.assertEqual(self.user.games, 0)
        self.assertEqual(self.user.daily_moves_remaining, DAILY_MOVES_LIMIT)


    def test_recalculate_player_stats_first_game(self):

        self.user.recalculate_player_stats(self.duration, self.error, self.score, self.moves)

        self.assertEqual(self.user.games, 1)
        self.assertEqual(self.user.daily_moves_remaining, DAILY_MOVES_LIMIT - 1)
        self.assertEqual(self.user.total_time, self.duration)
        self.assertEqual(self.user.total_errors, self.error)
        self.assertEqual(self.user.total_moves, self.moves)
        self.assertEqual(self.user.total_score, self.score)
        self.assertEqual(self.user.avg_time, self.user.total_time / self.user.games)
        self.assertEqual(self.user.avg_error, self.user.total_errors / self.user.games)
        self.assertEqual(self.user.avg_moves_per_game, self.user.total_moves / self.user.games)

    def test_recalculate_player_stats_multiple_games(self):
        # First game
        self.user.recalculate_player_stats(self.duration, self.error, self.score, self.moves)
        # Second game
        self.user.recalculate_player_stats(self.duration, self.error, self.score, self.moves)
        # Third game
        self.user.recalculate_player_stats(self.duration, self.error, self.score, self.moves)

        self.assertEqual(self.user.games, 3)
        self.assertEqual(self.user.daily_moves_remaining, DAILY_MOVES_LIMIT - 3)
        self.assertEqual(self.user.total_time, self.duration * 3)
        self.assertEqual(self.user.total_errors, self.error * 3)
        self.assertEqual(self.user.total_moves, self.moves * 3)
        self.assertEqual(self.user.total_score, self.score * 3)
        self.assertEqual(self.user.avg_time, self.user.total_time / self.user.games)
        self.assertEqual(self.user.avg_error, self.user.total_errors / self.user.games)
        self.assertEqual(self.user.avg_moves_per_game, self.user.total_moves / self.user.games)

class CheckTelegramAuthTest(TestCase):
    """
    Tests for check_telegram_auth function
    """
    @patch('users.views.BOT_TOKEN', 'test_token')
    def test_check_telegram_auth(self):
        """
        Test with valid data
        """
        test_data = 'user={"id":123456789,"username":"testuser"}'
        secret_key = hmac.new(b'WebAppData', b'test_token', hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, test_data.encode(), hashlib.sha256).hexdigest()
        raw_init_data = f"{test_data}&hash={computed_hash}"
        result = check_telegram_auth(raw_init_data)

        self.assertTrue(result)

    def test_check_telegram_auth_missing_hash(self):
        """
        Test without hash
        """
        raw_init_data = 'user={"id":123456789,"username":"testuser"}'
        result = check_telegram_auth(raw_init_data)

        self.assertFalse(result)

    @patch('users.views.BOT_TOKEN', 'test_token')
    def test_check_telegram_auth_invalid_hash(self):
        """
        Test with invalid hash
        """
        raw_init_data = 'user={"id":123456789,"username":"testuser"}&hash=invalid_hash'
        result = check_telegram_auth(raw_init_data)

        self.assertFalse(result)

class TelegramAuthViewTest(APITestCase):
    """
    Tests for TelegramAuthView
    """
    def setUp(self):
        self.url = reverse('telegram_auth')

    def test_telegram_auth_missing_init_data(self):
        """
        Test with missing init_data
        """
        response = self.client.post(self.url,{})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['error'], 'initData not provided')

    @patch('users.views.check_telegram_auth')
    def test_telegram_auth_invalid_signature(self, mock_check):
        """
        Test with invalid signature
        """
        mock_check.return_value = False
        response = self.client.post(self.url,{'initData':'test_data'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['error'], 'Invalid Telegram signature')

    @patch('users.views.check_telegram_auth')
    def test_telegram_auth_missing_user_data(self, mock_check):
        """
        Test with missing user data
        """
        mock_check.return_value = True
        response = self.client.post(self.url,{'initData':'hash=valid_hash'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['error'], 'User data is missing in initData')

    @patch('users.views.check_telegram_auth')
    def test_telegram_auth_new_user_creation(self, mock_check):
        """
        Test with new user creation
        """
        mock_check.return_value = True
        user_data = json.dumps({
            "id": 123456789,
            "username": "testuser"
        })
        init_data = f'user={user_data}&chatId=987654321&hash=valid_hash'
        response = self.client.post(self.url,{'initData': init_data})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check for creating user
        user = TelegramUser.objects.get(telegram_id="123456789")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.chat_id, 987654321)

        # Check for creating token
        token = Token.objects.get(user=user)
        self.assertIsNotNone(token)

        # Check for response data
        response_data = response.json()
        self.assertEqual(response_data['token'], token.key)
        self.assertEqual(response_data['user']['id'], user.id)
        self.assertEqual(response_data['user']['username'], user.username)

    @patch('users.views.check_telegram_auth')
    def test_telegram_auth_existing_user(self, mock_check):
        """
        Test with existing user
        """
        mock_check.return_value = True

        # Creating objects
        user = TelegramUser.objects.create(
            telegram_id = '123456789',
            username = 'testuser',
            chat_id = '987654321',
        )
        token = Token.objects.create(user=user)
        user_data = json.dumps({
            "id": 123456789,
            "username": "newusername"
        })

        # Creating api call
        init_data = f'user={user_data}&chatId=987654321&hash=valid_hash'
        response = self.client.post(self.url, {'initData': init_data})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh user data
        user.refresh_from_db()
        self.assertEqual(user.username, "newusername")

        # Check for response data
        response_data = response.json()
        self.assertEqual(response_data['token'], token.key)
        self.assertEqual(response_data['user']['id'], user.id)
        self.assertEqual(response_data['user']['username'], "newusername")

    @patch('users.views.check_telegram_auth')
    def test_telegram_auth_generating_username(self, mock_check):
        """
        Test with generating username
        """
        mock_check.return_value = True
        user_data =  json.dumps({
            "id": 123456789
        })

        init_data = f'user={user_data}&chatId=987654321&hash=valid_hash'
        response = self.client.post(self.url, {'initData': init_data})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check for autogenerated username
        user = TelegramUser.objects.get(telegram_id="123456789")
        self.assertEqual(user.username, "tg_123456789")

    @patch('users.views.check_telegram_auth')
    def test_telegram_auth_updating_chat_id_and_username(self, mock_check):
        """
        Test with updating chat_id and username
        """
        mock_check.return_value = True

        user = TelegramUser.objects.create(
            telegram_id = '123456789',
            username = 'testuser',
        )
        user_data = json.dumps({
            "id": 123456789,
            "username": "newusername"
        })
        init_data = f'user={user_data}&chatId=987654321&hash=valid_hash'

        response = self.client.post(self.url, {'initData': init_data})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        # Check for updating chat_id
        self.assertEqual(user.chat_id, 987654321)
        # Check for updating username
        self.assertEqual(user.username, "newusername")

class TelegramUserIntegrationTest(APITestCase):
    def setUp(self):
        self.url = reverse('telegram_auth')

    @patch('users.views.BOT_TOKEN', 'test_token')
    def test_full_authentication_flow(self):
        """
        Test full an authentication flow
        """

        user_data = {
            "id": 123456789,
            "username": "testuser"
        }
        params = {
            "user": json.dumps(user_data),
            "chatId": "987654321"
        }

        # Creating a valid signature
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret_key = hmac.new(b'WebAppData', b'test_token', hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        # Creating initData
        init_data_parts = [f"{k}={v}" for k, v in sorted(params.items())]
        init_data_parts.append(f"hash={computed_hash}")
        init_data = "&".join(init_data_parts)

        # Check for response
        response = self.client.post(self.url, {'initData': init_data})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check for creating user
        user = TelegramUser.objects.get(telegram_id="123456789")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.chat_id, 987654321)

        # Check for Token creating
        token = Token.objects.get(user=user)
        self.assertIsNotNone(token)

        # Check for answer structure
        response_data = response.json()
        self.assertIn('token', response_data)
        self.assertIn('user', response_data)
        self.assertEqual(response_data['user']['id'], user.id)
        self.assertEqual(response_data['user']['username'], user.username)
