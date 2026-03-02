"""
Management command to automatically sync employee LeetCode profiles.
This should be run periodically (e.g., via cron) to keep employee data up to date.

Usage:
    python manage.py sync_employee_profiles
    python manage.py sync_employee_profiles --company-id <uuid>
    python manage.py sync_employee_profiles --employee-id <uuid>
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.coding_platform_models import Employee, LeetCodeAnalysisHistory
from api.services.leetcode_service import LeetCodeService
from api.services.coding_profile_analysis_service import CodingProfileAnalysisService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync LeetCode profiles for employees with auto-sync enabled'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=str,
            help='Sync only employees for a specific company',
        )
        parser.add_argument(
            '--employee-id',
            type=str,
            help='Sync only a specific employee',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if not due yet',
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        employee_id = options.get('employee_id')
        force = options.get('force', False)
        
        # Build query
        employees = Employee.objects.filter(is_active=True, auto_sync_enabled=True)
        
        if company_id:
            employees = employees.filter(company_id=company_id)
        
        if employee_id:
            employees = employees.filter(id=employee_id)
        
        if not force:
            # Only sync employees whose next_sync time has passed
            employees = employees.filter(
                next_sync__lte=timezone.now()
            )
        
        total = employees.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No employees to sync.'))
            return
        
        self.stdout.write(f'Syncing {total} employee(s)...')
        
        successful = 0
        failed = 0
        
        for employee in employees:
            try:
                self.stdout.write(f'Syncing {employee.name} ({employee.leetcode_username})...')
                
                # Fetch stats
                stats_result = LeetCodeService.get_user_stats(employee.leetcode_username, 'Mid-Level')
                
                if not stats_result or 'error' in stats_result:
                    error_msg = stats_result.get('error', 'Failed to fetch stats') if stats_result else 'Failed to fetch stats'
                    self.stdout.write(self.style.ERROR(f'  Failed: {error_msg}'))
                    failed += 1
                    continue
                
                # Create analysis history record
                LeetCodeAnalysisHistory.objects.create(
                    company=employee.company,
                    employee_identifier=employee.leetcode_username,
                    leetcode_username=employee.leetcode_username,
                    leetcode_url=employee.leetcode_url,
                    total_solved=stats_result.get('total_solved', 0),
                    easy_solved=stats_result.get('easy_solved', 0),
                    medium_solved=stats_result.get('medium_solved', 0),
                    hard_solved=stats_result.get('hard_solved', 0),
                    problem_solving_score=stats_result.get('problem_solving_score', 0),
                    ranking=stats_result.get('ranking', 0),
                    acceptance_rate=stats_result.get('acceptance_rate', 0),
                    current_streak=stats_result.get('current_streak', 0),
                    max_streak=stats_result.get('max_streak', 0),
                    activity_status=stats_result.get('activity_status', 'Unknown'),
                    full_stats=stats_result,
                    analysis_data=stats_result.get('analysis', {}),
                )
                
                # Update employee last_synced and next_sync
                employee.last_synced = timezone.now()
                if employee.sync_frequency == 'daily':
                    employee.next_sync = timezone.now() + timedelta(days=1)
                elif employee.sync_frequency == 'weekly':
                    employee.next_sync = timezone.now() + timedelta(weeks=1)
                elif employee.sync_frequency == 'monthly':
                    employee.next_sync = timezone.now() + timedelta(days=30)
                employee.save()
                
                # Update goals
                from api.coding_platform_models import EmployeeGoal
                goals = EmployeeGoal.objects.filter(employee=employee, is_active=True)
                for goal in goals:
                    if goal.metric_type == 'total_solved':
                        goal.current_value = stats_result.get('total_solved', 0)
                    elif goal.metric_type == 'easy_solved':
                        goal.current_value = stats_result.get('easy_solved', 0)
                    elif goal.metric_type == 'medium_solved':
                        goal.current_value = stats_result.get('medium_solved', 0)
                    elif goal.metric_type == 'hard_solved':
                        goal.current_value = stats_result.get('hard_solved', 0)
                    elif goal.metric_type == 'problem_solving_score':
                        goal.current_value = stats_result.get('problem_solving_score', 0)
                    elif goal.metric_type == 'acceptance_rate':
                        goal.current_value = stats_result.get('acceptance_rate', 0)
                    elif goal.metric_type == 'current_streak':
                        goal.current_value = stats_result.get('current_streak', 0)
                    elif goal.metric_type == 'ranking':
                        goal.current_value = stats_result.get('ranking', 0)
                    
                    # Check if goal achieved
                    if goal.is_achieved and not goal.achieved_at:
                        goal.achieved_at = timezone.now()
                    
                    goal.save()
                
                self.stdout.write(self.style.SUCCESS(f'  Success: {stats_result.get("total_solved", 0)} problems solved'))
                successful += 1
                
            except Exception as e:
                logger.error(f"Error syncing employee {employee.id}: {str(e)}", exc_info=True)
                self.stdout.write(self.style.ERROR(f'  Error: {str(e)}'))
                failed += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Completed: {successful} successful, {failed} failed'))

