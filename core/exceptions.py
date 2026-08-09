# core/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    # Ita default handler kwanza
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "success": False,
            "error_type": exc.__class__.__name__,
            "message": response.data.get("detail", "Imetokea kosa wakati wa kuchakata ombi lako."),
            "errors": response.data if not isinstance(response.data.get("detail"), str) else None
        }
        response.data = custom_data
    else:
        # Kamata Server Errors zisizotarajiwa (500)
        return Response({
            "success": False,
            "error_type": "ServerError",
            "message": "Kitendo hiki kimeshindikana kwenye server. Tafadhali jaribu tena baadaye."
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response