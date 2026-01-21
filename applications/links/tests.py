from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from applications.accounts.models import User
from applications.links.models import Link

class LinkTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword'
        )
        self.client.force_authenticate(user=self.user)

        # Create links
        # 1. Active link
        Link.objects.create(
            owner=self.user,
            original_url='http://example.com/1',
            is_active=True,
            click_count=10
        )
        # 2. Inactive link
        Link.objects.create(
            owner=self.user,
            original_url='http://example.com/2',
            is_active=False,
            click_count=5
        )
        # 3. Expired link
        Link.objects.create(
            owner=self.user,
            original_url='http://example.com/3',
            is_active=True,
            expires_at=timezone.now() - timedelta(days=1),
            click_count=3
        )
        # 4. Soft deleted link
        Link.objects.create(
            owner=self.user,
            original_url='http://example.com/4',
            deleted_at=timezone.now(),
            click_count=2
        )

    def test_stats_aggregation(self):
        """Test stats endpoint uses aggregation correctly"""
        url = reverse('link-list') + 'stats/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        
        # User has 3 non-deleted links (1 active, 1 inactive, 1 expired/active)
        # Note: expired link is still "is_active=True" in DB usually, but expired property handles logic.
        # But stats endpoint counts based on is_active flags mainly.
        # Let's check logic: inactive_links = is_active=False. active_links=is_active=True.
        # Expired link has is_active=True in my setup above.
        
        self.assertEqual(data['total_links'], 3)
        self.assertEqual(data['active_links'], 2) # link 1 and 3
        self.assertEqual(data['inactive_links'], 1) # link 2
        self.assertEqual(data['total_clicks'], 10 + 5 + 3) # 18

    def test_filter_active(self):
        """Test filtering by is_active"""
        url = reverse('link-list')
        response = self.client.get(url, {'is_active': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return link 1 and 3
        self.assertEqual(len(response.data['results']), 2)

        response = self.client.get(url, {'is_active': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return link 2
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_expired(self):
        """Test filtering by expired"""
        url = reverse('link-list')
        
        # expired=true -> should get link 3
        response = self.client.get(url, {'expired': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['original_url'], 'http://example.com/3')

        # expired=false -> should get active links (link 1)
        # Note: LinkManager.active() implementation:
        # return self.filter(is_active=True, deleted_at__isnull=True).exclude(expires_at__lt=timezone.now())
        # Link 2 is is_active=False, so it shouldn't be in active()
        # Link 3 is expired, so it shouldn't be in active()
        # So only Link 1
        
        response = self.client.get(url, {'expired': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['original_url'], 'http://example.com/1')
