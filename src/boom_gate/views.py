"""
Boom Gate Views
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .controller import boom_gate_controller
import json
import logging

logger = logging.getLogger(__name__)


def boom_gate_control(request):
    """Boom gate control panel view"""
    context = {
        'title': 'Boom Gate Control',
        'gate_status': boom_gate_controller.get_gate_status()
    }
    return render(request, 'boom_gate_control.html', context)


@csrf_exempt
def gate_status_api(request):
    """API endpoint for gate status"""
    try:
        status = boom_gate_controller.get_gate_status()
        return JsonResponse({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting gate status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt  
def gate_control_api(request):
    """API endpoint for gate control commands"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        command = data.get('command')
        
        if command == 'open':
            # Direct gate control via API
            transaction_id = data.get('transaction_id', 'api_test')
            vehicle_plate = data.get('vehicle_plate', 'API-TEST')
            
            try:
                from .sync_controller import trigger_gate_sync
                
                success = trigger_gate_sync(
                    transaction_id=transaction_id,
                    vehicle_plate=vehicle_plate,
                    open_duration=data.get('open_duration', 5)
                )
                
                if success:
                    return JsonResponse({
                        'success': True,
                        'message': f'Boom gate opened for {vehicle_plate}',
                        'transaction_id': transaction_id
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Failed to trigger gate operation'
                    }, status=500)
                    
            except Exception as e:
                logger.error(f"API gate open error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)
            
        elif command == 'emergency_stop':
            try:
                from .sync_controller import emergency_stop_sync
                
                success = emergency_stop_sync()
                
                return JsonResponse({
                    'success': success,
                    'message': 'Emergency stop activated' if success else 'Emergency stop failed'
                })
                
            except Exception as e:
                logger.error(f"API emergency stop error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)
            
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown command: {command}'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in gate control API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
