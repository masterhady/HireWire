from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from datetime import datetime
from api.coding_platform_models import Employee, EmployeeGoal, LeetCodeAnalysisHistory
import logging

logger = logging.getLogger(__name__)


class EmployeeGoalViewSet(APIView):
    """
    Manage goals for employees.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id=None):
        """Get goals for an employee or all employees."""
        try:
            if employee_id:
                # Goals for specific employee
                try:
                    employee = Employee.objects.get(id=employee_id, company=request.user)
                except Employee.DoesNotExist:
                    return Response(
                        {"error": "Employee not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                goals = EmployeeGoal.objects.filter(employee=employee).order_by('-created_at')
                
                # Filter by status
                status_filter = request.query_params.get('status')
                if status_filter == 'active':
                    goals = goals.filter(is_active=True, achieved_at__isnull=True)
                elif status_filter == 'achieved':
                    goals = goals.filter(achieved_at__isnull=False)
                elif status_filter == 'inactive':
                    goals = goals.filter(is_active=False)
                
                goals_data = []
                for goal in goals:
                    goals_data.append({
                        'id': str(goal.id),
                        'metric_type': goal.metric_type,
                        'metric_display': goal.get_metric_type_display(),
                        'target_value': goal.target_value,
                        'current_value': goal.current_value,
                        'start_value': goal.start_value,
                        'progress_percentage': round(goal.progress_percentage, 1),
                        'is_achieved': goal.is_achieved,
                        'start_date': goal.start_date.isoformat(),
                        'target_date': goal.target_date.isoformat(),
                        'achieved_at': goal.achieved_at.isoformat() if goal.achieved_at else None,
                        'is_active': goal.is_active,
                        'notes': goal.notes,
                        'days_remaining': (goal.target_date - timezone.now()).days if not goal.is_achieved else None,
                    })
                
                return Response(goals_data, status=status.HTTP_200_OK)
            else:
                # All goals for company
                goals = EmployeeGoal.objects.filter(company=request.user).order_by('-created_at')
                
                # Filter by status
                status_filter = request.query_params.get('status')
                if status_filter == 'active':
                    goals = goals.filter(is_active=True, achieved_at__isnull=True)
                elif status_filter == 'achieved':
                    goals = goals.filter(achieved_at__isnull=False)
                
                goals_data = []
                for goal in goals:
                    goals_data.append({
                        'id': str(goal.id),
                        'employee_id': str(goal.employee.id),
                        'employee_name': goal.employee.name,
                        'metric_type': goal.metric_type,
                        'metric_display': goal.get_metric_type_display(),
                        'target_value': goal.target_value,
                        'current_value': goal.current_value,
                        'start_value': goal.start_value,
                        'progress_percentage': round(goal.progress_percentage, 1),
                        'is_achieved': goal.is_achieved,
                        'target_date': goal.target_date.isoformat(),
                        'achieved_at': goal.achieved_at.isoformat() if goal.achieved_at else None,
                        'is_active': goal.is_active,
                    })
                
                return Response(goals_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching goals: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to fetch goals: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Create a new goal."""
        try:
            employee_id = request.data.get('employee_id')
            if not employee_id:
                return Response(
                    {"error": "employee_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                employee = Employee.objects.get(id=employee_id, company=request.user)
            except Employee.DoesNotExist:
                return Response(
                    {"error": "Employee not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get current value from latest history
            latest = LeetCodeAnalysisHistory.objects.filter(
                company=request.user,
                employee_identifier=employee.leetcode_username
            ).order_by('-analyzed_at').first()
            
            # Determine start value based on metric type
            start_value = 0
            if latest:
                metric_type = request.data.get('metric_type')
                if metric_type == 'total_solved':
                    start_value = latest.total_solved
                elif metric_type == 'easy_solved':
                    start_value = latest.easy_solved
                elif metric_type == 'medium_solved':
                    start_value = latest.medium_solved
                elif metric_type == 'hard_solved':
                    start_value = latest.hard_solved
                elif metric_type == 'problem_solving_score':
                    start_value = latest.problem_solving_score
                elif metric_type == 'acceptance_rate':
                    start_value = latest.acceptance_rate
                elif metric_type == 'current_streak':
                    start_value = latest.current_streak
                elif metric_type == 'ranking':
                    start_value = latest.ranking
            
            # Create goal
            goal = EmployeeGoal.objects.create(
                employee=employee,
                company=request.user,
                metric_type=request.data.get('metric_type'),
                target_value=float(request.data.get('target_value')),
                start_value=start_value,
                current_value=start_value,
                target_date=datetime.fromisoformat(request.data.get('target_date').replace('Z', '+00:00')) if request.data.get('target_date') else timezone.now() + timezone.timedelta(days=30),
                notes=request.data.get('notes'),
            )
            
            return Response({
                'id': str(goal.id),
                'message': 'Goal created successfully',
                'progress_percentage': round(goal.progress_percentage, 1),
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating goal: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to create goal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, goal_id=None):
        """Update a goal."""
        try:
            if not goal_id:
                return Response(
                    {"error": "goal_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            goal = EmployeeGoal.objects.get(id=goal_id, company=request.user)
            
            # Update fields
            if 'target_value' in request.data:
                goal.target_value = float(request.data['target_value'])
            if 'target_date' in request.data:
                goal.target_date = datetime.fromisoformat(request.data['target_date'].replace('Z', '+00:00'))
            if 'is_active' in request.data:
                goal.is_active = request.data['is_active']
            if 'notes' in request.data:
                goal.notes = request.data['notes']
            
            goal.save()
            
            return Response({
                'id': str(goal.id),
                'message': 'Goal updated successfully',
                'progress_percentage': round(goal.progress_percentage, 1),
            }, status=status.HTTP_200_OK)
        except EmployeeGoal.DoesNotExist:
            return Response(
                {"error": "Goal not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating goal: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to update goal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, goal_id=None):
        """Delete (deactivate) a goal."""
        try:
            if not goal_id:
                return Response(
                    {"error": "goal_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            goal = EmployeeGoal.objects.get(id=goal_id, company=request.user)
            goal.is_active = False
            goal.save()
            
            return Response(
                {"message": "Goal deactivated successfully"},
                status=status.HTTP_200_OK
            )
        except EmployeeGoal.DoesNotExist:
            return Response(
                {"error": "Goal not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deactivating goal: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Failed to deactivate goal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

