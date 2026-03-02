from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from api.coding_platform_models import CodingProfile
from api.services.leetcode_service import LeetCodeService
from api.services.hackerrank_service import HackerRankService
from api.services.coding_profile_analysis_service import CodingProfileAnalysisService
from rest_framework import serializers
from urllib.parse import urlparse

def extract_username_from_url(username_input, platform):
    """
    Extracts username from URL if a URL is provided, otherwise returns the input as-is.
    Handles formats like:
    - https://leetcode.com/u/username/
    - https://leetcode.com/username/
    - https://www.hackerrank.com/profile/username
    - Just 'username' (returns as-is)
    """
    if not username_input:
        return username_input
    
    # If it doesn't look like a URL, return as-is
    if not (username_input.startswith('http://') or username_input.startswith('https://')):
        return username_input.strip()
    
    try:
        parsed = urlparse(username_input)
        path = parsed.path.strip('/')
        
        if platform == 'leetcode':
            # Handle formats: /u/username/ or /username/
            parts = path.split('/')
            if len(parts) >= 2 and parts[0] == 'u':
                return parts[1]
            elif len(parts) >= 1:
                return parts[-1]  # Last part is usually the username
        elif platform == 'hackerrank':
            # Handle format: /profile/username
            parts = path.split('/')
            if len(parts) >= 2 and parts[0] == 'profile':
                return parts[1]
            elif len(parts) >= 1:
                return parts[-1]
        
        # Fallback: return last part of path
        return path.split('/')[-1] if path else username_input
    except Exception:
        # If parsing fails, return original input
        return username_input

class CodingProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodingProfile
        fields = ['id', 'platform', 'username', 'url', 'stats', 'analysis', 'last_synced', 'created_at']
        read_only_fields = ['stats', 'analysis', 'last_synced', 'created_at']

class CodingProfileViewSet(viewsets.ModelViewSet):
    serializer_class = CodingProfileSerializer
    permission_classes = [IsAuthenticated]
    # Don't override authentication_classes - use default from REST_FRAMEWORK settings

    def get_queryset(self):
        try:
            if not self.request.user or self.request.user.is_anonymous:
                return CodingProfile.objects.none()
            return CodingProfile.objects.filter(user=self.request.user)
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in get_queryset: {str(e)}")
            return CodingProfile.objects.none()

    def perform_create(self, serializer):
        try:
            if not self.request.user or self.request.user.is_anonymous:
                raise serializers.ValidationError("User must be authenticated")
            
            platform = serializer.validated_data.get('platform')
            username_input = serializer.validated_data.get('username')
            
            # Extract username from URL if a URL was provided
            username = extract_username_from_url(username_input, platform)
            
            # Auto-generate URL if not provided
            url = serializer.validated_data.get('url')
            if not url:
                if platform == 'leetcode':
                    url = f"https://leetcode.com/u/{username}/"
                elif platform == 'hackerrank':
                    url = f"https://www.hackerrank.com/profile/{username}"
            
            # Save with cleaned username
            serializer.save(user=self.request.user, username=username, url=url)
        except serializers.ValidationError:
            raise
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in perform_create: {str(e)}")
            raise serializers.ValidationError(f"Failed to create profile: {str(e)}")

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            profile = self.get_object()
            stats = None
            error_message = None
            
            try:
                # Extract username from URL if stored as URL
                actual_username = extract_username_from_url(profile.username, profile.platform)
                
                if profile.platform == 'leetcode':
                    logger.info(f"Syncing LeetCode profile for user: {actual_username} (original: {profile.username})")
                    stats = LeetCodeService.get_user_stats(actual_username)
                elif profile.platform == 'hackerrank':
                    logger.info(f"Syncing HackerRank profile for user: {actual_username} (original: {profile.username})")
                    stats = HackerRankService.get_user_stats(actual_username)
                else:
                    return Response(
                        {"error": f"Unsupported platform: {profile.platform}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Update username in database if it was a URL (clean it up)
                if actual_username != profile.username:
                    profile.username = actual_username
                    logger.info(f"Updated username from URL to: {actual_username}")
            except Exception as e:
                logger.error(f"Exception while fetching stats for {profile.platform} user {profile.username}: {str(e)}")
                error_message = f"Error connecting to {profile.platform}: {str(e)}"
                actual_username = extract_username_from_url(profile.username, profile.platform)
                # Still try to clean up username even if fetch fails
                if actual_username != profile.username:
                    profile.username = actual_username
                    username_updated = True
                    profile.save()  # Save username cleanup even if stats fetch failed
                
            if stats:
                profile.stats = stats
                profile.last_synced = timezone.now()
                
                # Trigger AI Analysis
                try:
                    analysis = CodingProfileAnalysisService.analyze_profile(profile)
                    if analysis:
                        profile.analysis = analysis
                except Exception as e:
                    logger.warning(f"Failed to generate AI analysis: {str(e)}")
                    # Continue even if analysis fails
                
                profile.save()
                return Response(self.get_serializer(profile).data)
            else:
                # Provide more specific error message
                if error_message:
                    return Response(
                        {"error": error_message},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    return Response(
                        {
                            "error": f"Failed to fetch stats from {profile.platform}. Please verify the username '{profile.username}' is correct and try again.",
                            "platform": profile.platform,
                            "username": profile.username
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
        except Exception as e:
            logger.error(f"Unexpected error in sync action: {str(e)}")
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
