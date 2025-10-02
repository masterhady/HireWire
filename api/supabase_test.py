from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse

def test_supabase_connection(request):
    db_conn = connections['default']
    try:
        db_conn.cursor()
        return JsonResponse({'status': 'success', 'message': 'Connected to Supabase PostgreSQL database.'})
    except OperationalError as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
