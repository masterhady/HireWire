from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Q, Avg, Max, Min, Count, F, Sum
from django.utils import timezone
from datetime import timedelta
from api.coding_platform_models import Employee, EmployeeGoal, LeetCodeAnalysisHistory
from api.services.leetcode_service import LeetCodeService
from api.services.coding_profile_analysis_service import CodingProfileAnalysisService
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def extract_username_from_leetcode_url(url):
    """Extract username from LeetCode URL."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        parts = path.split('/')
        if len(parts) >= 2 and parts[0] == 'u':
            return parts[1]
        elif len(parts) >= 1:
            return parts[-1]
        return None
    except Exception:
        return None


class EmployeeViewSet(APIView):
    """
    Manage employees for problem-solving progress tracking.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all employees for the company."""
        try:
            employees = Employee.objects.filter(company=request.user, is_active=True)
            
            # Optional filters
            team = request.query_params.get('team')
            if team:
                employees = employees.filter(team=team)
            
            # Get latest stats for each employee
            employee_data = []
            for employee in employees:
                latest_history = LeetCodeAnalysisHistory.objects.filter(
                    company=request.user,
                    employee_identifier=employee.leetcode_username
                ).order_by('-analyzed_at').first()
                
                # Get active goals
                active_goals = employee.goals.filter(is_active=True).count()
                achieved_goals = employee.goals.filter(achieved_at__isnull=False).count()
                
                employee_data.append({
                    'id': str(employee.id),
                    'name': employee.name,
                    'email': employee.email,
                    'employee_id': employee.employee_id,
                    'leetcode_username': employee.leetcode_username,
                    'leetcode_url': employee.leetcode_url,
                    'team': employee.team,
                    'role': employee.role,
                    'auto_sync_enabled': employee.auto_sync_enabled,
                    'sync_frequency': employee.sync_frequency,
                    'last_synced': employee.last_synced.isoformat() if employee.last_synced else None,
                    'next_sync': employee.next_sync.isoformat() if employee.next_sync else None,
                    'notes': employee.notes,
                    'latest_stats': {
                        'total_solved': latest_history.total_solved if latest_history else 0,
                        'problem_solving_score': latest_history.problem_solving_score if latest_history else 0,
                        'analyzed_at': latest_history.analyzed_at.isoformat() if latest_history else None,
                    } if latest_history else None,
                    'active_goals': active_goals,
                    'achieved_goals': achieved_goals,
                    'created_at': employee.created_at.isoformat(),
                })
            
            return Response(employee_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching employees: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to fetch employees: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Create a new employee."""
        try:
            leetcode_url = request.data.get('leetcode_url')
            if not leetcode_url:
                return Response(
                    {"error": "leetcode_url is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            leetcode_username = extract_username_from_leetcode_url(leetcode_url)
            if not leetcode_username:
                return Response(
                    {"error": "Invalid LeetCode URL format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if employee already exists
            existing = Employee.objects.filter(
                company=request.user,
                leetcode_username=leetcode_username
            ).first()
            
            if existing:
                return Response(
                    {"error": f"Employee with LeetCode username '{leetcode_username}' already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create employee
            employee = Employee.objects.create(
                company=request.user,
                name=request.data.get('name', leetcode_username),
                email=request.data.get('email'),
                employee_id=request.data.get('employee_id'),
                leetcode_username=leetcode_username,
                leetcode_url=leetcode_url,
                team=request.data.get('team'),
                role=request.data.get('role'),
                auto_sync_enabled=request.data.get('auto_sync_enabled', False),
                sync_frequency=request.data.get('sync_frequency', 'weekly'),
                notes=request.data.get('notes'),
            )
            
            # Calculate next sync time
            if employee.auto_sync_enabled:
                if employee.sync_frequency == 'daily':
                    employee.next_sync = timezone.now() + timedelta(days=1)
                elif employee.sync_frequency == 'weekly':
                    employee.next_sync = timezone.now() + timedelta(weeks=1)
                elif employee.sync_frequency == 'monthly':
                    employee.next_sync = timezone.now() + timedelta(days=30)
                employee.save()
            
            return Response({
                'id': str(employee.id),
                'name': employee.name,
                'leetcode_username': employee.leetcode_username,
                'message': 'Employee created successfully'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating employee: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to create employee: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, employee_id=None):
        """Update an employee."""
        try:
            if not employee_id:
                return Response(
                    {"error": "employee_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            employee = Employee.objects.get(id=employee_id, company=request.user)
            
            # Update fields
            if 'name' in request.data:
                employee.name = request.data['name']
            if 'email' in request.data:
                employee.email = request.data['email']
            if 'employee_id' in request.data:
                employee.employee_id = request.data['employee_id']
            if 'team' in request.data:
                employee.team = request.data['team']
            if 'role' in request.data:
                employee.role = request.data['role']
            if 'auto_sync_enabled' in request.data:
                employee.auto_sync_enabled = request.data['auto_sync_enabled']
            if 'sync_frequency' in request.data:
                employee.sync_frequency = request.data['sync_frequency']
            if 'notes' in request.data:
                employee.notes = request.data['notes']
            if 'is_active' in request.data:
                employee.is_active = request.data['is_active']
            
            # Recalculate next_sync if sync settings changed
            if 'auto_sync_enabled' in request.data or 'sync_frequency' in request.data:
                if employee.auto_sync_enabled:
                    if employee.sync_frequency == 'daily':
                        employee.next_sync = timezone.now() + timedelta(days=1)
                    elif employee.sync_frequency == 'weekly':
                        employee.next_sync = timezone.now() + timedelta(weeks=1)
                    elif employee.sync_frequency == 'monthly':
                        employee.next_sync = timezone.now() + timedelta(days=30)
                else:
                    employee.next_sync = None
            
            employee.save()
            
            return Response({
                'id': str(employee.id),
                'message': 'Employee updated successfully'
            }, status=status.HTTP_200_OK)
        except Employee.DoesNotExist:
            return Response(
                {"error": "Employee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating employee: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to update employee: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, employee_id=None):
        """Delete (deactivate) an employee."""
        try:
            if not employee_id:
                return Response(
                    {"error": "employee_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            employee = Employee.objects.get(id=employee_id, company=request.user)
            employee.is_active = False
            employee.save()
            
            return Response(
                {"message": "Employee deactivated successfully"},
                status=status.HTTP_200_OK
            )
        except Employee.DoesNotExist:
            return Response(
                {"error": "Employee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deactivating employee: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to deactivate employee: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmployeeProgressView(APIView):
    """
    Track employee progress over time with historical comparisons.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id=None):
        """Get progress data for an employee or all employees."""
        try:
            if employee_id:
                # Single employee progress
                try:
                    employee = Employee.objects.get(id=employee_id, company=request.user)
                except Employee.DoesNotExist:
                    return Response(
                        {"error": "Employee not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Get historical data
                history = LeetCodeAnalysisHistory.objects.filter(
                    company=request.user,
                    employee_identifier=employee.leetcode_username
                ).order_by('analyzed_at')
                
                # Calculate progress metrics
                progress_data = []
                previous_stats = None
                
                for record in history:
                    if previous_stats:
                        progress_data.append({
                            'date': record.analyzed_at.isoformat(),
                            'total_solved': record.total_solved,
                            'total_solved_change': record.total_solved - previous_stats['total_solved'],
                            'easy_solved': record.easy_solved,
                            'easy_solved_change': record.easy_solved - previous_stats['easy_solved'],
                            'medium_solved': record.medium_solved,
                            'medium_solved_change': record.medium_solved - previous_stats['medium_solved'],
                            'hard_solved': record.hard_solved,
                            'hard_solved_change': record.hard_solved - previous_stats['hard_solved'],
                            'problem_solving_score': record.problem_solving_score,
                            'score_change': record.problem_solving_score - previous_stats['problem_solving_score'],
                            'ranking': record.ranking,
                            'ranking_change': previous_stats['ranking'] - record.ranking,  # Lower is better
                            'acceptance_rate': record.acceptance_rate,
                            'acceptance_rate_change': record.acceptance_rate - previous_stats['acceptance_rate'],
                            'current_streak': record.current_streak,
                            'streak_change': record.current_streak - previous_stats['current_streak'],
                        })
                    else:
                        progress_data.append({
                            'date': record.analyzed_at.isoformat(),
                            'total_solved': record.total_solved,
                            'total_solved_change': 0,
                            'easy_solved': record.easy_solved,
                            'easy_solved_change': 0,
                            'medium_solved': record.medium_solved,
                            'medium_solved_change': 0,
                            'hard_solved': record.hard_solved,
                            'hard_solved_change': 0,
                            'problem_solving_score': record.problem_solving_score,
                            'score_change': 0,
                            'ranking': record.ranking,
                            'ranking_change': 0,
                            'acceptance_rate': record.acceptance_rate,
                            'acceptance_rate_change': 0,
                            'current_streak': record.current_streak,
                            'streak_change': 0,
                        })
                    
                    previous_stats = {
                        'total_solved': record.total_solved,
                        'easy_solved': record.easy_solved,
                        'medium_solved': record.medium_solved,
                        'hard_solved': record.hard_solved,
                        'problem_solving_score': record.problem_solving_score,
                        'ranking': record.ranking,
                        'acceptance_rate': record.acceptance_rate,
                        'current_streak': record.current_streak,
                    }
                
                # Get latest and previous records for comparison
                latest = history.last()
                previous = history.order_by('-analyzed_at')[1] if history.count() > 1 else None
                
                # Calculate growth rates
                growth_metrics = {}
                if latest and previous:
                    days_diff = (latest.analyzed_at - previous.analyzed_at).days
                    if days_diff > 0:
                        growth_metrics = {
                            'total_solved_growth_rate': ((latest.total_solved - previous.total_solved) / days_diff) * 7,  # per week
                            'score_growth_rate': ((latest.problem_solving_score - previous.problem_solving_score) / days_diff) * 7,
                            'period_days': days_diff,
                        }
                
                return Response({
                    'employee': {
                        'id': str(employee.id),
                        'name': employee.name,
                        'leetcode_username': employee.leetcode_username,
                    },
                    'latest_stats': {
                        'total_solved': latest.total_solved if latest else 0,
                        'problem_solving_score': latest.problem_solving_score if latest else 0,
                        'analyzed_at': latest.analyzed_at.isoformat() if latest else None,
                    } if latest else None,
                    'previous_stats': {
                        'total_solved': previous.total_solved if previous else 0,
                        'problem_solving_score': previous.problem_solving_score if previous else 0,
                        'analyzed_at': previous.analyzed_at.isoformat() if previous else None,
                    } if previous else None,
                    'progress_timeline': progress_data,
                    'growth_metrics': growth_metrics,
                    'total_records': history.count(),
                }, status=status.HTTP_200_OK)
            else:
                # All employees summary
                employees = Employee.objects.filter(company=request.user, is_active=True)
                
                # Get date range filter
                days_back = int(request.query_params.get('days', 30))
                start_date = timezone.now() - timedelta(days=days_back)
                
                summary = []
                for employee in employees:
                    latest = LeetCodeAnalysisHistory.objects.filter(
                        company=request.user,
                        employee_identifier=employee.leetcode_username,
                        analyzed_at__gte=start_date
                    ).order_by('-analyzed_at').first()
                    
                    previous = LeetCodeAnalysisHistory.objects.filter(
                        company=request.user,
                        employee_identifier=employee.leetcode_username,
                        analyzed_at__lt=latest.analyzed_at if latest else timezone.now()
                    ).order_by('-analyzed_at').first() if latest else None
                    
                    if latest:
                        summary.append({
                            'employee_id': str(employee.id),
                            'employee_name': employee.name,
                            'leetcode_username': employee.leetcode_username,
                            'team': employee.team,
                            'latest_total_solved': latest.total_solved,
                            'latest_score': latest.problem_solving_score,
                            'total_solved_change': latest.total_solved - (previous.total_solved if previous else 0),
                            'score_change': latest.problem_solving_score - (previous.problem_solving_score if previous else 0),
                            'last_analyzed': latest.analyzed_at.isoformat(),
                        })
                
                return Response({
                    'summary': summary,
                    'total_employees': employees.count(),
                    'period_days': days_back,
                }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching progress: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to fetch progress: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class KPIDashboardView(APIView):
    """
    Comprehensive KPI dashboard with aggregated metrics for problem-solving skills.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get KPI metrics for the company."""
        try:
            # Get date range
            days_back = int(request.query_params.get('days', 30))
            start_date = timezone.now() - timedelta(days=days_back)
            
            # Get all active employees
            employees = Employee.objects.filter(company=request.user, is_active=True)
            employee_count = employees.count()
            
            if employee_count == 0:
                return Response({
                    'employee_count': 0,
                    'message': 'No employees found. Add employees to start tracking KPIs.'
                }, status=status.HTTP_200_OK)
            
            # Get latest stats for all employees
            latest_stats = []
            for employee in employees:
                latest = LeetCodeAnalysisHistory.objects.filter(
                    company=request.user,
                    employee_identifier=employee.leetcode_username,
                    analyzed_at__gte=start_date
                ).order_by('-analyzed_at').first()
                
                if latest:
                    latest_stats.append({
                        'employee_id': str(employee.id),
                        'employee_name': employee.name,
                        'team': employee.team,
                        'total_solved': latest.total_solved,
                        'easy_solved': latest.easy_solved,
                        'medium_solved': latest.medium_solved,
                        'hard_solved': latest.hard_solved,
                        'problem_solving_score': latest.problem_solving_score,
                        'ranking': latest.ranking,
                        'acceptance_rate': latest.acceptance_rate,
                        'current_streak': latest.current_streak,
                        'analyzed_at': latest.analyzed_at,
                    })
            
            if not latest_stats:
                return Response({
                    'employee_count': employee_count,
                    'message': 'No analysis data found for the selected period.'
                }, status=status.HTTP_200_OK)
            
            # Calculate aggregated KPIs
            total_solved_avg = sum(s['total_solved'] for s in latest_stats) / len(latest_stats)
            score_avg = sum(s['problem_solving_score'] for s in latest_stats) / len(latest_stats)
            acceptance_rate_avg = sum(s['acceptance_rate'] for s in latest_stats) / len(latest_stats)
            streak_avg = sum(s['current_streak'] for s in latest_stats) / len(latest_stats)
            
            # Team breakdown
            teams = {}
            for stat in latest_stats:
                team = stat['team'] or 'Unassigned'
                if team not in teams:
                    teams[team] = {
                        'employee_count': 0,
                        'total_solved_sum': 0,
                        'score_sum': 0,
                        'members': []
                    }
                teams[team]['employee_count'] += 1
                teams[team]['total_solved_sum'] += stat['total_solved']
                teams[team]['score_sum'] += stat['problem_solving_score']
                teams[team]['members'].append(stat['employee_name'])
            
            # Calculate team averages
            team_metrics = []
            for team_name, team_data in teams.items():
                team_metrics.append({
                    'team': team_name,
                    'employee_count': team_data['employee_count'],
                    'avg_total_solved': team_data['total_solved_sum'] / team_data['employee_count'],
                    'avg_score': team_data['score_sum'] / team_data['employee_count'],
                    'members': team_data['members'],
                })
            
            # Top performers
            top_solvers = sorted(latest_stats, key=lambda x: x['total_solved'], reverse=True)[:5]
            top_scores = sorted(latest_stats, key=lambda x: x['problem_solving_score'], reverse=True)[:5]
            most_consistent = sorted(latest_stats, key=lambda x: x['current_streak'], reverse=True)[:5]
            
            # Growth analysis (compare with previous period)
            previous_start = start_date - timedelta(days=days_back)
            growth_data = []
            for stat in latest_stats:
                employee = employees.get(id=stat['employee_id'])
                previous = LeetCodeAnalysisHistory.objects.filter(
                    company=request.user,
                    employee_identifier=employee.leetcode_username,
                    analyzed_at__gte=previous_start,
                    analyzed_at__lt=start_date
                ).order_by('-analyzed_at').first()
                
                if previous:
                    growth_data.append({
                        'employee_name': stat['employee_name'],
                        'total_solved_growth': stat['total_solved'] - previous.total_solved,
                        'score_growth': stat['problem_solving_score'] - previous.problem_solving_score,
                    })
            
            avg_growth = {
                'total_solved_growth': sum(g['total_solved_growth'] for g in growth_data) / len(growth_data) if growth_data else 0,
                'score_growth': sum(g['score_growth'] for g in growth_data) / len(growth_data) if growth_data else 0,
            } if growth_data else None
            
            return Response({
                'period': {
                    'days': days_back,
                    'start_date': start_date.isoformat(),
                    'end_date': timezone.now().isoformat(),
                },
                'overview': {
                    'total_employees': employee_count,
                    'employees_with_data': len(latest_stats),
                    'avg_total_solved': round(total_solved_avg, 1),
                    'avg_problem_solving_score': round(score_avg, 1),
                    'avg_acceptance_rate': round(acceptance_rate_avg, 1),
                    'avg_current_streak': round(streak_avg, 1),
                },
                'team_metrics': team_metrics,
                'top_performers': {
                    'top_solvers': [
                        {
                            'name': s['employee_name'],
                            'total_solved': s['total_solved'],
                            'team': s['team'],
                        }
                        for s in top_solvers
                    ],
                    'top_scores': [
                        {
                            'name': s['employee_name'],
                            'score': s['problem_solving_score'],
                            'team': s['team'],
                        }
                        for s in top_scores
                    ],
                    'most_consistent': [
                        {
                            'name': s['employee_name'],
                            'streak': s['current_streak'],
                            'team': s['team'],
                        }
                        for s in most_consistent
                    ],
                },
                'growth_analysis': {
                    'avg_growth': avg_growth,
                    'employees_with_growth_data': len(growth_data),
                } if growth_data else None,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching KPI dashboard: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to fetch KPI dashboard: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SyncEmployeeView(APIView):
    """
    Manually sync an employee's LeetCode profile and save to history.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, employee_id=None):
        """Sync employee profile."""
        try:
            if not employee_id:
                return Response(
                    {"error": "employee_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            employee = Employee.objects.get(id=employee_id, company=request.user)
            
            # Fetch stats
            target_role = request.data.get('target_role', 'Mid-Level')
            stats_result = LeetCodeService.get_user_stats(employee.leetcode_username, target_role)
            
            if not stats_result or 'error' in stats_result:
                error_msg = stats_result.get('error', 'Failed to fetch stats') if stats_result else 'Failed to fetch stats'
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create analysis history record
            history = LeetCodeAnalysisHistory.objects.create(
                company=request.user,
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
            
            # Update employee last_synced
            employee.last_synced = timezone.now()
            if employee.auto_sync_enabled:
                if employee.sync_frequency == 'daily':
                    employee.next_sync = timezone.now() + timedelta(days=1)
                elif employee.sync_frequency == 'weekly':
                    employee.next_sync = timezone.now() + timedelta(weeks=1)
                elif employee.sync_frequency == 'monthly':
                    employee.next_sync = timezone.now() + timedelta(days=30)
            employee.save()
            
            # Update goals
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
            
            return Response({
                'message': 'Employee synced successfully',
                'history_id': str(history.id),
                'stats': {
                    'total_solved': history.total_solved,
                    'problem_solving_score': history.problem_solving_score,
                },
                'goals_updated': goals.count(),
            }, status=status.HTTP_200_OK)
        except Employee.DoesNotExist:
            return Response(
                {"error": "Employee not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error syncing employee: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to sync employee: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

