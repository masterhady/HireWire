import requests
import logging

logger = logging.getLogger(__name__)

class LeetCodeService:
    BASE_URL = "https://leetcode.com/graphql"

    @staticmethod
    def get_user_stats(username, target_role="Mid-Level"):
        """
        Fetches user statistics from LeetCode using their GraphQL API.
        """
        query = """
        query getUserProfile($username: String!) {
            matchedUser(username: $username) {
                username
                submissionCalendar
                submitStats: submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                        submissions
                    }
                }
                profile {
                    ranking
                    reputation
                    starRating
                    realName
                    userAvatar
                    countryName
                    company
                    school
                }
            }
        }
        """

        variables = {"username": username}

        try:
            # First, try a simpler query to check if user exists
            simple_check_query = """
            query userPublicProfile($username: String!) {
                matchedUser(username: $username) {
                    username
                    submissionCalendar
                    profile {
                        ranking
                    }
                }
            }
            """
            
            # Try simple query first
            simple_response = requests.post(
                LeetCodeService.BASE_URL,
                json={'query': simple_check_query, 'variables': variables},
                headers={
                    'Content-Type': 'application/json',
                    'Referer': 'https://leetcode.com',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Origin': 'https://leetcode.com'
                },
                timeout=15
            )
            
            logger.debug(f"LeetCode simple check response status: {simple_response.status_code} for user {username}")
            
            if simple_response.status_code != 200:
                logger.error(f"LeetCode API returned status {simple_response.status_code} for user {username}")
                return {
                    'error': f'LeetCode API returned error status {simple_response.status_code}. The service may be temporarily unavailable.',
                    'username': username,
                    'exists': None
                }
            
            simple_data = simple_response.json()
            
            if 'errors' in simple_data:
                error_details = simple_data.get('errors', [])
                error_messages = [err.get('message', str(err)) for err in error_details]
                logger.error(f"LeetCode API errors for user {username}: {error_messages}")
                return {
                    'error': f'LeetCode API error: {", ".join(error_messages)}',
                    'username': username,
                    'exists': None
                }
            
            simple_matched = simple_data.get('data', {}).get('matchedUser')
            if not simple_matched:
                logger.warning(f"LeetCode user '{username}' not found in simple check. Response data: {simple_data}")
                # Log the full response for debugging
                logger.debug(f"Full LeetCode API response for {username}: {simple_data}")
                return {
                    'error': f'User "{username}" does not exist on LeetCode or profile is private.',
                    'username': username,
                    'exists': False
                }
            
            # User exists, now get full stats
            response = requests.post(
                LeetCodeService.BASE_URL,
                json={'query': query, 'variables': variables},
                headers={
                    'Content-Type': 'application/json',
                    'Referer': 'https://leetcode.com',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Origin': 'https://leetcode.com'
                },
                timeout=15
            )
            
            logger.debug(f"LeetCode API full query response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"LeetCode API returned status {response.status_code} for full query user {username}")
                logger.error(f"Response text: {response.text[:500]}")
                # User exists but we can't get full stats - try to get basic info from simple query
                profile = simple_matched.get('profile', {})
                # Try to get submitStats from simple_matched if available
                simple_stats = simple_matched.get('submitStats', {})
                simple_ac = simple_stats.get('acSubmissionNum', []) if simple_stats else []
                
                total_solved = 0
                for stat in simple_ac:
                    if stat.get('difficulty') == 'All':
                        total_solved = stat.get('count', 0)
                        break
                
                # Try to get submissionCalendar from simple_matched
                calendar_str = simple_matched.get('submissionCalendar', '{}')
                import json
                submission_calendar = json.loads(calendar_str)

                return {
                    'total_solved': total_solved,
                    'easy_solved': 0,
                    'medium_solved': 0,
                    'hard_solved': 0,
                    'total_submissions': 0,
                    'acceptance_rate': 0,
                    'ranking': profile.get('ranking', 0),
                    'reputation': profile.get('reputation', 0),
                    'star_rating': profile.get('starRating', 0),
                    'real_name': profile.get('realName', ''),
                    'avatar': profile.get('userAvatar', ''),
                    'country': profile.get('countryName', ''),
                    'company': profile.get('company', ''),
                    'school': profile.get('school', ''),
                    'error': 'Could not fetch complete statistics. Some data may be missing.',
                    'username': username,
                    'submission_calendar': submission_calendar
                }
                
            response.raise_for_status()
            data = response.json()
            
            # Log the full response for debugging
            logger.debug(f"Full LeetCode API response for {username}: {data}")

            if 'errors' in data:
                error_details = data.get('errors', [])
                error_messages = [err.get('message', str(err)) for err in error_details]
                logger.error(f"LeetCode API error for user {username}: {error_messages}")
                # User exists (we checked earlier), but full query failed
                profile = simple_matched.get('profile', {})
                # Try to get submissionCalendar from simple_matched
                calendar_str = simple_matched.get('submissionCalendar', '{}')
                import json
                submission_calendar = json.loads(calendar_str)

                # Get partial stats from simple query if available
                simple_stats = simple_matched.get('submitStats', {})
                simple_ac = simple_stats.get('acSubmissionNum', []) if simple_stats else []
                total_solved = 0
                for stat in simple_ac:
                    if stat.get('difficulty') == 'All':
                        total_solved = stat.get('count', 0)
                        break

                return {
                    'total_solved': total_solved,
                    'easy_solved': 0,
                    'medium_solved': 0,
                    'hard_solved': 0,
                    'total_submissions': 0,
                    'acceptance_rate': 0,
                    'ranking': profile.get('ranking', 0),
                    'reputation': profile.get('reputation', 0),
                    'star_rating': profile.get('starRating', 0),
                    'real_name': profile.get('realName', ''),
                    'avatar': profile.get('userAvatar', ''),
                    'country': profile.get('countryName', ''),
                    'company': profile.get('company', ''),
                    'school': profile.get('school', ''),
                    'error': f'Could not fetch full statistics. API errors: {", ".join(error_messages)}',
                    'username': username,
                    'submission_calendar': submission_calendar
                }

            matched_user = data.get('data', {}).get('matchedUser')
            if not matched_user:
                # This shouldn't happen since we checked earlier, but handle it
                logger.warning(f"LeetCode user '{username}' matchedUser is null in full query")
                profile = simple_matched.get('profile', {})
                # Try to get submissionCalendar from simple_matched
                calendar_str = simple_matched.get('submissionCalendar', '{}')
                import json
                submission_calendar = json.loads(calendar_str)
                
                # Get partial stats from simple query if available
                simple_stats = simple_matched.get('submitStats', {})
                simple_ac = simple_stats.get('acSubmissionNum', []) if simple_stats else []
                total_solved = 0
                for stat in simple_ac:
                    if stat.get('difficulty') == 'All':
                        total_solved = stat.get('count', 0)
                        break

                # Return partial stats with a specific error message
                return {
                    'total_solved': total_solved,
                    'easy_solved': 0,
                    'medium_solved': 0,
                    'hard_solved': 0,
                    'total_submissions': 0,
                    'acceptance_rate': 0,
                    'ranking': profile.get('ranking', 0),
                    'reputation': profile.get('reputation', 0),
                    'star_rating': profile.get('starRating', 0),
                    'real_name': profile.get('realName', ''),
                    'avatar': profile.get('userAvatar', ''),
                    'country': profile.get('countryName', ''),
                    'company': profile.get('company', ''),
                    'school': profile.get('school', ''),
                    'error': 'Profile is private. Showing limited public information.',
                    'username': username,
                    'submission_calendar': submission_calendar
                }

            stats = matched_user.get('submitStats', {})
            if not stats:
                logger.warning(f"LeetCode user '{username}' has no submission stats")
                return {
                    'error': 'User profile exists but has no submission statistics. The user may not have solved any problems yet.',
                    'username': username,
                    'exists': True
                }
            
            ac_submission_num = stats.get('acSubmissionNum', [])
            if not ac_submission_num or len(ac_submission_num) == 0:
                logger.warning(f"LeetCode user '{username}' has empty submission stats array")
                profile = matched_user.get('profile', {})
                return {
                    'error': 'User profile exists but has no solved problems or submission history.',
                    'username': username,
                    'exists': True,
                    'ranking': profile.get('ranking', 0),
                    'reputation': profile.get('reputation', 0),
                }
            
            profile = matched_user.get('profile', {})
            # Contest ranking removed from query as it's not available on UserNode
            
            # Log the raw stats for debugging
            logger.debug(f"Raw stats for {username}: {ac_submission_num}")
            
            # Calculate total submissions and acceptance rate
            total_submissions = 0
            total_accepted = 0
            found_all_difficulty = False
            
            for stat in ac_submission_num:
                difficulty = stat.get('difficulty', '')
                count = stat.get('count', 0)
                submissions = stat.get('submissions', 0)
                
                logger.debug(f"Processing stat: difficulty={difficulty}, count={count}, submissions={submissions}")
                
                if difficulty == 'All':
                    total_accepted = count
                    total_submissions = submissions
                    found_all_difficulty = True
                elif difficulty == 'Easy':
                    total_submissions += submissions
                elif difficulty == 'Medium':
                    total_submissions += submissions
                elif difficulty == 'Hard':
                    total_submissions += submissions
            
            # If we didn't find "All" difficulty, something is wrong with the data structure
            if not found_all_difficulty:
                logger.warning(f"LeetCode user '{username}' stats missing 'All' difficulty entry. Stats: {ac_submission_num}")
                # Try to calculate from individual difficulties
                total_accepted = sum(s.get('count', 0) for s in ac_submission_num if s.get('difficulty') != 'All')
            
            acceptance_rate = (total_accepted / total_submissions * 100) if total_submissions > 0 else 0
            
            # If all stats are zero, the user likely has no activity
            if total_accepted == 0 and total_submissions == 0:
                logger.warning(f"LeetCode user '{username}' has zero solved problems and zero submissions")
                return {
                    'error': 'User profile exists but has no solved problems or submission history.',
                    'username': username,
                    'exists': True,
                    'ranking': profile.get('ranking', 0),
                    'reputation': profile.get('reputation', 0),
                }
            
            # Parse submission calendar
            calendar_str = matched_user.get('submissionCalendar', '{}')
            import json
            submission_calendar = json.loads(calendar_str)

            # Parse stats into a cleaner format
            parsed_stats = {
                'total_solved': 0,
                'easy_solved': 0,
                'medium_solved': 0,
                'hard_solved': 0,
                'total_submissions': total_submissions,
                'acceptance_rate': round(acceptance_rate, 2),
                'ranking': profile.get('ranking', 0),
                'reputation': profile.get('reputation', 0),
                'star_rating': profile.get('starRating', 0),
                'real_name': profile.get('realName', ''),
                'avatar': profile.get('userAvatar', ''),
                'country': profile.get('countryName', ''),
                'company': profile.get('company', ''),
                'school': profile.get('school', ''),
                'submission_calendar': submission_calendar,
            }

            for stat in ac_submission_num:
                difficulty = stat.get('difficulty', '')
                count = stat.get('count', 0)
                if difficulty == 'All':
                    parsed_stats['total_solved'] = count
                elif difficulty == 'Easy':
                    parsed_stats['easy_solved'] = count
                elif difficulty == 'Medium':
                    parsed_stats['medium_solved'] = count
                elif difficulty == 'Hard':
                    parsed_stats['hard_solved'] = count
            
            # Contest information not available in current API structure
            # Can be added later if needed with a separate query

            # Final validation - if total_solved is 0, check if user actually has any activity
            if parsed_stats['total_solved'] == 0 and parsed_stats['ranking'] == 0:
                logger.warning(f"LeetCode user '{username}' appears to have no activity (all zeros)")
                # Still return the data but log it
                logger.debug(f"Returning stats for {username}: {parsed_stats}")
            
            # Calculate advanced metrics
            advanced_metrics = LeetCodeService.calculate_advanced_metrics(parsed_stats, target_role)
            parsed_stats.update(advanced_metrics)
            
            logger.info(f"Successfully fetched LeetCode stats for {username}: {parsed_stats['total_solved']} problems solved, ranking: {parsed_stats['ranking']}")
            return parsed_stats

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching LeetCode stats for {username}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching LeetCode stats for {username}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching LeetCode stats for {username}: {str(e)}", exc_info=True)
            return None


    @staticmethod
    def calculate_advanced_metrics(stats, target_role="Mid-Level"):
        """
        Calculates advanced metrics with role-based weighting and returns a detailed breakdown.
        """
        try:
            # Define Weight Profiles
            weights = {
                "Intern": {
                    "difficulty": 0.20, "quality": 0.20, "consistency": 0.30, "ranking": 0.20, "engagement": 0.10
                },
                "Mid-Level": {
                    "difficulty": 0.30, "quality": 0.25, "consistency": 0.25, "ranking": 0.15, "engagement": 0.05
                },
                "Senior": {
                    "difficulty": 0.40, "quality": 0.30, "consistency": 0.15, "ranking": 0.10, "engagement": 0.05
                }
            }
            
            role_weights = weights.get(target_role, weights["Mid-Level"])
            
            # 1. Weighted Acceptance Rate
            easy = stats.get('easy_solved', 0)
            medium = stats.get('medium_solved', 0)
            hard = stats.get('hard_solved', 0)
            total_solved = stats.get('total_solved', 1) or 1
            
            avg_problem_difficulty = ((easy * 1) + (medium * 2) + (hard * 3)) / total_solved
            raw_acceptance_rate = stats.get('acceptance_rate', 0)
            
            weighted_acceptance_rate = raw_acceptance_rate * (avg_problem_difficulty / 1.5)
            weighted_acceptance_rate = min(100, round(weighted_acceptance_rate, 2))

            # 2. Consistency & Activity
            submission_calendar = stats.get('submission_calendar', {})
            current_streak = 0
            max_streak = 0
            avg_weekly_submissions = 0
            active_status = "Inactive"
            
            if submission_calendar:
                timestamps = sorted([int(ts) for ts in submission_calendar.keys()])
                if timestamps:
                    import datetime
                    dates = [datetime.datetime.fromtimestamp(ts).date() for ts in timestamps]
                    today = datetime.date.today()
                    
                    # Status
                    last_submission_date = dates[-1]
                    if (today - last_submission_date).days <= 30:
                        active_status = "Active"
                        
                    # Streak Logic
                    unique_dates = sorted(list(set(dates)))
                    if unique_dates:
                        temp_streak = 1
                        max_streak = 1
                        for i in range(1, len(unique_dates)):
                            if (unique_dates[i] - unique_dates[i-1]).days == 1:
                                temp_streak += 1
                            else:
                                temp_streak = 1
                            max_streak = max(max_streak, temp_streak)
                        
                        if (today - unique_dates[-1]).days <= 1:
                            current_streak = 1
                            for i in range(len(unique_dates)-2, -1, -1):
                                if (unique_dates[i+1] - unique_dates[i]).days == 1:
                                    current_streak += 1
                                else:
                                    break
                        else:
                            current_streak = 0

                    # Avg Weekly
                    first_date = dates[0]
                    total_days = (today - first_date).days
                    if total_days > 0:
                        weeks = total_days / 7
                        total_subs = sum(submission_calendar.values())
                        avg_weekly_submissions = round(total_subs / max(1, weeks), 1)

            # 3. Community Engagement
            reputation = stats.get('reputation', 0)
            engagement_level = "Low"
            if reputation > 2000: engagement_level = "High"
            elif reputation > 500: engagement_level = "Medium"
                
            # 4. Role-Based Score Calculation
            
            # Component Scores (0-100)
            # Difficulty: Based on Hard/Medium ratio and total volume
            # Target: 50 Hard problems = 100 points for Difficulty?
            comp_difficulty = min((hard * 2 + medium * 0.5) / 100, 1.0) * 100
            
            # Quality Score: Based on Weighted Acceptance Rate
            comp_quality = min(weighted_acceptance_rate / 80, 1.0) * 100 # 80% weighted AR is perfect
            
            # Consistency Score: Based on Streak and Weekly Avg
            # Target: 30 day streak or 5 subs/week
            comp_consistency = min((max_streak / 30) * 0.6 + (avg_weekly_submissions / 5) * 0.4, 1.0) * 100
            
            # Ranking/Volume Score: Total solved and global ranking
            # Target: 500 problems or Top 5%
            comp_ranking = min(stats.get('total_solved', 0) / 500, 1.0) * 100
            
            # Engagement Score: Reputation
            # Target: 1000 reputation
            comp_engagement = min(reputation / 1000, 1.0) * 100
            
            # Calculate Weighted Total
            w = role_weights
            final_score = (
                comp_difficulty * w['difficulty'] +
                comp_quality * w['quality'] +
                comp_consistency * w['consistency'] +
                comp_ranking * w['ranking'] +
                comp_engagement * w['engagement']
            )
            
            unified_score = round(final_score)
            
            
            # Generate personalized recommendations
            recommendations = []
            
            # Difficulty Coverage
            if comp_difficulty < 40:
                recommendations.append("Solve more medium and hard problems to improve difficulty coverage.")
            elif comp_difficulty < 70:
                recommendations.append("Focus on hard problems to reach advanced difficulty coverage.")
            
            # Solution Quality
            if comp_quality < 50:
                recommendations.append("Improve acceptance rate by reviewing solutions before submission and testing edge cases.")
            
            # Consistency
            if comp_consistency < 40:
                recommendations.append("Build longer active streaks by solving problems regularly (aim for daily practice).")
            elif current_streak == 0 and max_streak > 0:
                recommendations.append("Resume your practice streak to maintain consistency.")
            
            # Volume/Ranking
            if comp_ranking < 50:
                recommendations.append("Increase total problems solved to improve your global ranking.")
            
            # Community Engagement
            if comp_engagement < 30:
                recommendations.append("Engage with the community by sharing solutions and participating in discussions.")
            
            # Limit to top 3 most impactful recommendations
            # Prioritize based on component weights
            weighted_gaps = []
            if comp_difficulty < 70:
                weighted_gaps.append(('difficulty', (100 - comp_difficulty) * w['difficulty']))
            if comp_quality < 70:
                weighted_gaps.append(('quality', (100 - comp_quality) * w['quality']))
            if comp_consistency < 70:
                weighted_gaps.append(('consistency', (100 - comp_consistency) * w['consistency']))
            if comp_ranking < 70:
                weighted_gaps.append(('ranking', (100 - comp_ranking) * w['ranking']))
            
            weighted_gaps.sort(key=lambda x: x[1], reverse=True)
            recommendations = recommendations[:3]  # Limit to 3
            
            score_breakdown = {
                "total": unified_score,
                "role": target_role,
                "components": {
                    "difficulty": {
                        "label": "Difficulty Coverage",
                        "score": round(comp_difficulty),
                        "weight": w['difficulty'],
                        "value": f"{hard} Hard, {medium} Medium"
                    },
                    "quality": {
                        "label": "Solution Quality",
                        "score": round(comp_quality),
                        "weight": w['quality'],
                        "value": f"{weighted_acceptance_rate}% Weighted AR"
                    },
                    "consistency": {
                        "label": "Consistency",
                        "score": round(comp_consistency),
                        "weight": w['consistency'],
                        "value": f"{max_streak} Day Streak"
                    },
                    "ranking": {
                        "label": "Volume & Ranking",
                        "score": round(comp_ranking),
                        "weight": w['ranking'],
                        "value": f"{stats.get('total_solved')} Solved"
                    },
                    "engagement": {
                        "label": "Community Engagement",
                        "score": round(comp_engagement),
                        "weight": w['engagement'],
                        "value": f"{reputation} Rep"
                    }
                },
                "recommendations": recommendations
            }
            
            return {
                'weighted_acceptance_rate': weighted_acceptance_rate,
                'current_streak': current_streak,
                'max_streak': max_streak,
                'avg_weekly_submissions': avg_weekly_submissions,
                'activity_status': active_status,
                'community_engagement': engagement_level,
                'problem_solving_score': unified_score,
                'score_breakdown': score_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error calculating advanced metrics: {str(e)}")
            return {
                'weighted_acceptance_rate': 0,
                'current_streak': 0,
                'max_streak': 0,
                'avg_weekly_submissions': 0,
                'activity_status': "Unknown",
                'community_engagement': "Low",
                'problem_solving_score': 0,
                'score_breakdown': None
            }
