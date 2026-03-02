# Employee Problem-Solving Progress Tracking & KPI Guide

## Overview

This guide covers the enhanced problem-solving tracking features for company accounts. These features allow you to monitor your employees' progress in problem-solving skills (LeetCode) and measure this as a KPI.

## Features

### 1. Employee Management
- **Add Employees**: Save employee profiles with their LeetCode usernames
- **Team Organization**: Group employees by team/department
- **Auto-Sync**: Enable automatic periodic syncing (daily, weekly, monthly)
- **Employee Metadata**: Store additional info like email, employee ID, role, notes

### 2. Progress Tracking
- **Historical Data**: Track progress over time with historical snapshots
- **Trend Analysis**: Compare current vs previous performance
- **Growth Metrics**: Calculate growth rates (problems solved per week, score improvements)
- **Timeline View**: See progress changes over time

### 3. KPI Dashboard
- **Aggregated Metrics**: Team averages, company-wide statistics
- **Top Performers**: Identify top solvers, highest scores, most consistent
- **Team Breakdown**: Compare performance across teams/departments
- **Growth Analysis**: Track overall improvement trends

### 4. Goal Setting & Tracking
- **Set Goals**: Create goals for specific metrics (total solved, score, acceptance rate, etc.)
- **Progress Tracking**: Automatic progress calculation and percentage
- **Goal Achievement**: Automatic detection when goals are met
- **Multiple Goals**: Set multiple goals per employee

### 5. Automated Syncing
- **Scheduled Updates**: Automatic periodic syncing based on frequency settings
- **Manual Sync**: Trigger immediate sync for specific employees
- **Goal Updates**: Goals automatically update when profiles are synced

## API Endpoints

### Employee Management

#### Get All Employees
```
GET /api/company/employees/
Query params: ?team=<team_name>
```

#### Create Employee
```
POST /api/company/employees/
Body: {
    "name": "John Doe",
    "email": "john@company.com",
    "employee_id": "EMP001",
    "leetcode_url": "https://leetcode.com/u/johndoe/",
    "team": "Engineering",
    "role": "Software Engineer",
    "auto_sync_enabled": true,
    "sync_frequency": "weekly",  // daily, weekly, monthly
    "notes": "Senior developer"
}
```

#### Update Employee
```
PATCH /api/company/employees/<employee_id>/
Body: {
    "team": "New Team",
    "auto_sync_enabled": false,
    ...
}
```

#### Delete Employee (Deactivate)
```
DELETE /api/company/employees/<employee_id>/
```

#### Sync Employee Profile
```
POST /api/company/employees/<employee_id>/sync/
Body: {
    "target_role": "Mid-Level"  // Optional: Intern, Mid-Level, Senior
}
```

### Progress Tracking

#### Get Employee Progress
```
GET /api/company/employees/<employee_id>/progress/
```

Returns:
- Latest and previous stats
- Progress timeline with changes
- Growth metrics (problems per week, score growth)
- Total records count

#### Get All Employees Progress Summary
```
GET /api/company/progress/
Query params: ?days=30  // Number of days to look back
```

### KPI Dashboard

#### Get KPI Dashboard
```
GET /api/company/kpi-dashboard/
Query params: ?days=30  // Period for analysis
```

Returns:
- Overview metrics (averages, totals)
- Team breakdown and comparisons
- Top performers (solvers, scores, consistency)
- Growth analysis

### Goal Management

#### Get Employee Goals
```
GET /api/company/employees/<employee_id>/goals/
Query params: ?status=active  // active, achieved, inactive
```

#### Get All Company Goals
```
GET /api/company/goals/
Query params: ?status=active
```

#### Create Goal
```
POST /api/company/employees/<employee_id>/goals/
Body: {
    "metric_type": "total_solved",  // total_solved, easy_solved, medium_solved, 
                                    // hard_solved, problem_solving_score, 
                                    // acceptance_rate, current_streak, ranking
    "target_value": 500,
    "target_date": "2025-12-31T00:00:00Z",
    "notes": "Reach 500 problems by end of year"
}
```

#### Update Goal
```
PATCH /api/company/goals/<goal_id>/
Body: {
    "target_value": 600,
    "target_date": "2026-01-31T00:00:00Z",
    "is_active": true
}
```

#### Delete Goal (Deactivate)
```
DELETE /api/company/goals/<goal_id>/
```

## Automated Syncing

### Management Command

Run the sync command periodically (e.g., via cron):

```bash
# Sync all employees due for sync
python manage.py sync_employee_profiles

# Sync specific company
python manage.py sync_employee_profiles --company-id <uuid>

# Sync specific employee
python manage.py sync_employee_profiles --employee-id <uuid>

# Force sync (ignore next_sync time)
python manage.py sync_employee_profiles --force
```

### Cron Setup Example

Add to crontab for daily sync at 2 AM:
```
0 2 * * * cd /path/to/project && python manage.py sync_employee_profiles
```

## Usage Workflow

### 1. Initial Setup

1. **Add Employees**: Create employee records with their LeetCode profiles
2. **Enable Auto-Sync**: Set sync frequency for automatic updates
3. **Set Goals**: Create goals for employees to track progress

### 2. Regular Monitoring

1. **View KPI Dashboard**: Check overall team performance
2. **Review Progress**: Monitor individual employee progress
3. **Track Goals**: See goal achievement status
4. **Export Data**: Use existing export features for reports

### 3. Analysis & Reporting

1. **Compare Periods**: Use date filters to compare performance
2. **Team Comparison**: Analyze team-level metrics
3. **Identify Trends**: Review growth metrics and trends
4. **Top Performers**: Recognize high achievers

## Key Metrics Tracked

### Problem-Solving Metrics
- **Total Problems Solved**: Overall count
- **By Difficulty**: Easy, Medium, Hard breakdown
- **Problem Solving Score**: 0-100 unified score
- **Acceptance Rate**: Success rate on submissions
- **Ranking**: Global LeetCode ranking

### Consistency Metrics
- **Current Streak**: Days of consecutive activity
- **Max Streak**: Best streak achieved
- **Activity Status**: Active/Inactive status
- **Weekly Average**: Average submissions per week

### Growth Metrics
- **Problems Solved Growth**: Change over time
- **Score Growth**: Improvement in problem-solving score
- **Growth Rate**: Problems per week, score per week

## Best Practices

1. **Regular Syncing**: Enable auto-sync for consistent data
2. **Set Realistic Goals**: Create achievable goals with clear deadlines
3. **Team Organization**: Use team field to group employees
4. **Monitor Trends**: Review KPI dashboard regularly
5. **Celebrate Achievements**: Use goal achievements to recognize progress

## Integration with Existing Features

- **Analysis History**: All analyses are automatically saved to `LeetCodeAnalysisHistory`
- **Export Features**: Use existing Excel/CSV/PDF export with historical data
- **Batch Analysis**: Continue using batch analysis, results are saved to history

## Database Models

### Employee
- Stores employee information and LeetCode profile
- Tracks sync settings and schedule
- Links to company account

### EmployeeGoal
- Defines goals for specific metrics
- Tracks progress and achievement
- Calculates progress percentage automatically

### LeetCodeAnalysisHistory
- Stores historical snapshots of analysis
- Enables progress tracking over time
- Indexed for efficient queries

## Next Steps

1. **Run Migrations**: Create database tables for new models
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Set Up Cron**: Configure automated syncing

3. **Add Employees**: Start adding employee profiles

4. **Set Goals**: Create initial goals for tracking

5. **Monitor Dashboard**: Use KPI dashboard for insights

## Support

For issues or questions, check:
- API documentation
- Error logs in Django admin
- Management command output

