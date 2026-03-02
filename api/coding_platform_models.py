from django.db import models
from django.conf import settings
import uuid

class CodingProfile(models.Model):
    """
    Stores a user's profile information from external coding platforms.
    """
    PLATFORM_CHOICES = [
        ('leetcode', 'LeetCode'),
        ('hackerrank', 'HackerRank'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coding_profiles')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    username = models.CharField(max_length=100)
    url = models.URLField(blank=True, null=True)
    stats = models.JSONField(default=dict, blank=True) # Stores the fetched stats (e.g., solved count, ranking)
    analysis = models.JSONField(default=dict, blank=True) # Stores AI-generated analysis (strengths, weaknesses, tips)
    last_synced = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'platform']
        ordering = ['platform']

    def __str__(self):
        return f"{self.user.username} - {self.platform} ({self.username})"


class LeetCodeAnalysisHistory(models.Model):
    """
    Stores historical snapshots of LeetCode analysis results for progress tracking.
    Allows companies to monitor employee skill development over time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leetcode_history')
    
    # Employee identification
    employee_identifier = models.CharField(max_length=255, help_text="Username or CSV name")
    leetcode_username = models.CharField(max_length=100, blank=True, null=True)
    leetcode_url = models.URLField()
    
    # Timestamp
    analyzed_at = models.DateTimeField(auto_now_add=True)
    
    # Key metrics (for quick queries and charts)
    total_solved = models.IntegerField(default=0)
    easy_solved = models.IntegerField(default=0)
    medium_solved = models.IntegerField(default=0)
    hard_solved = models.IntegerField(default=0)
    problem_solving_score = models.IntegerField(default=0, help_text="Score out of 100")
    ranking = models.IntegerField(default=0)
    acceptance_rate = models.FloatField(default=0.0)
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    activity_status = models.CharField(max_length=20, blank=True, null=True)
    
    # Full data as JSON for flexibility
    full_stats = models.JSONField(default=dict, help_text="Complete stats from LeetCode API")
    analysis_data = models.JSONField(default=dict, help_text="AI analysis results")
    
    class Meta:
        ordering = ['-analyzed_at']
        indexes = [
            models.Index(fields=['company', 'employee_identifier', '-analyzed_at']),
            models.Index(fields=['company', '-analyzed_at']),
        ]
        verbose_name_plural = "LeetCode Analysis Histories"
    
    def __str__(self):
        return f"{self.employee_identifier} - {self.analyzed_at.strftime('%Y-%m-%d %H:%M')}"


class Employee(models.Model):
    """
    Manages employee profiles for companies to track problem-solving progress.
    Links employees to their LeetCode profiles and tracks metadata.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employees')
    
    # Employee identification
    name = models.CharField(max_length=255, help_text="Employee name or identifier")
    email = models.EmailField(blank=True, null=True)
    employee_id = models.CharField(max_length=100, blank=True, null=True, help_text="Internal employee ID")
    
    # LeetCode profile
    leetcode_username = models.CharField(max_length=100)
    leetcode_url = models.URLField()
    
    # Team/Department grouping
    team = models.CharField(max_length=100, blank=True, null=True, help_text="Team or department name")
    role = models.CharField(max_length=100, blank=True, null=True, help_text="Job role/title")
    
    # Tracking settings
    auto_sync_enabled = models.BooleanField(default=False, help_text="Enable automatic periodic syncing")
    sync_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='weekly',
        help_text="How often to automatically sync this employee's profile"
    )
    last_synced = models.DateTimeField(blank=True, null=True)
    next_sync = models.DateTimeField(blank=True, null=True, help_text="Next scheduled sync time")
    
    # Metadata
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about the employee")
    is_active = models.BooleanField(default=True, help_text="Whether this employee is currently being tracked")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['company', 'leetcode_username']
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['company', 'team']),
            models.Index(fields=['company', '-last_synced']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.company.username})"


class EmployeeGoal(models.Model):
    """
    Allows companies to set goals for employees and track progress.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='goals')
    company = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_goals')
    
    # Goal details
    metric_type = models.CharField(
        max_length=50,
        choices=[
            ('total_solved', 'Total Problems Solved'),
            ('easy_solved', 'Easy Problems Solved'),
            ('medium_solved', 'Medium Problems Solved'),
            ('hard_solved', 'Hard Problems Solved'),
            ('problem_solving_score', 'Problem Solving Score'),
            ('acceptance_rate', 'Acceptance Rate'),
            ('current_streak', 'Current Streak'),
            ('ranking', 'Ranking (lower is better)'),
        ]
    )
    target_value = models.FloatField(help_text="Target value to achieve")
    current_value = models.FloatField(default=0, help_text="Current value (updated on sync)")
    start_value = models.FloatField(default=0, help_text="Value when goal was set")
    
    # Timeline
    start_date = models.DateTimeField(auto_now_add=True)
    target_date = models.DateTimeField(help_text="Deadline for achieving the goal")
    achieved_at = models.DateTimeField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-target_date', '-created_at']
        indexes = [
            models.Index(fields=['employee', 'is_active']),
            models.Index(fields=['company', 'is_active', '-target_date']),
        ]
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage towards goal."""
        if self.target_value == self.start_value:
            return 0
        if self.metric_type == 'ranking':
            # For ranking, lower is better, so we invert the calculation
            if self.start_value == 0:
                return 0
            progress = ((self.start_value - self.current_value) / (self.start_value - self.target_value)) * 100
            return max(0, min(100, progress))
        else:
            progress = ((self.current_value - self.start_value) / (self.target_value - self.start_value)) * 100
            return max(0, min(100, progress))
    
    @property
    def is_achieved(self):
        """Check if goal has been achieved."""
        if self.achieved_at:
            return True
        if self.metric_type == 'ranking':
            return self.current_value <= self.target_value
        return self.current_value >= self.target_value
    
    def __str__(self):
        return f"{self.employee.name} - {self.get_metric_type_display()}: {self.current_value}/{self.target_value}"
