import requests
import jwt
import time
from django.conf import settings


class ZoomService:
    """Service for Zoom API integration."""
    
    BASE_URL = 'https://api.zoom.us/v2'
    
    def __init__(self):
        self.api_key = settings.ZOOM_API_KEY
        self.api_secret = settings.ZOOM_API_SECRET
        self.account_id = settings.ZOOM_ACCOUNT_ID
    
    def _get_access_token(self):
        """Get OAuth access token for Zoom API."""
        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={self.account_id}"
        
        import base64
        credentials = base64.b64encode(
            f"{self.api_key}:{self.api_secret}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(url, headers=headers, timeout=30)
            data = response.json()
            return data.get('access_token')
        except requests.RequestException:
            return None
    
    def _get_headers(self):
        """Get headers with access token."""
        token = self._get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def create_meeting(self, topic, start_time, duration=60, timezone='Africa/Abidjan'):
        """Create a Zoom meeting."""
        url = f"{self.BASE_URL}/users/me/meetings"
        
        payload = {
            'topic': topic,
            'type': 2,
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'duration': duration,
            'timezone': timezone,
            'settings': {
                'host_video': True,
                'participant_video': True,
                'join_before_host': False,
                'mute_upon_entry': True,
                'waiting_room': True,
                'auto_recording': 'none'
            }
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 201:
                data = response.json()
                return {
                    'success': True,
                    'meeting_id': str(data['id']),
                    'join_url': data['join_url'],
                    'start_url': data['start_url'],
                    'password': data.get('password', '')
                }
            else:
                return {
                    'success': False,
                    'error': response.json().get('message', 'Erreur de création')
                }
        except requests.RequestException as e:
            return {'success': False, 'error': str(e)}
    
    def get_meeting(self, meeting_id):
        """Get meeting details."""
        url = f"{self.BASE_URL}/meetings/{meeting_id}"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': 'Meeting not found'}
        except requests.RequestException as e:
            return {'success': False, 'error': str(e)}
    
    def delete_meeting(self, meeting_id):
        """Delete a meeting."""
        url = f"{self.BASE_URL}/meetings/{meeting_id}"
        
        try:
            response = requests.delete(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            
            return response.status_code == 204
        except requests.RequestException:
            return False
    
    def get_recordings(self, meeting_id):
        """Get meeting recordings."""
        url = f"{self.BASE_URL}/meetings/{meeting_id}/recordings"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': 'No recordings found'}
        except requests.RequestException as e:
            return {'success': False, 'error': str(e)}
