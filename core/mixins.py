import logging

logger = logging.getLogger(__name__)

class AuthenticatedMixin:
    def get_user(self, request):
        user = request.user
        if not user.is_authenticated:
            logger.warning(f'Unauthorized access attempt from {request.META.get("REMOTE_ADDR")}')
            return None
        return request.user