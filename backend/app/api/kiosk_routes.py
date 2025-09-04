from flask import Blueprint, request, jsonify
from ..services.billing_service import BillingService
from ..services.coupon_service import CouponService
from ..utils.db_connector import db_connector

kiosk_bp = Blueprint('kiosk', __name__, url_prefix='/api/v1/kiosk')

@kiosk_bp.route('/fee', methods=['GET'])
def get_parking_fee():
    """
    Query parking fee by license plate
    GET /api/v1/kiosk/fee%splate=ABC-1234
    """
    try:
        plate = request.args.get('plate')
        if not plate:
            return jsonify({'error': 'License plate parameter is required'}), 400
        
        # Find active parking record for this plate
        query = """
            SELECT pr.RecordID, pr.VehicleNumber, pr.EntryTime, pr.ParkingLotID, pl.Name as LotName
            FROM PARKING_RECORD pr
            JOIN PARKING_LOT pl ON pr.ParkingLotID = pl.ParkingLotID
            WHERE pr.VehicleNumber = %s AND pr.ExitTime IS NULL
            ORDER BY pr.EntryTime DESC
        """
        
        result = db_connector.execute_query(query, (plate,))
        
        if not result:
            return jsonify({'message': '找不到此車輛的在場紀錄。'}), 404
        
        record = result[0]
        
        # Calculate current fee
        fee_info = BillingService.calculate_parking_fee(record['RecordID'])
        
        return jsonify({
            'recordId': record['RecordID'],
            'licensePlate': record['VehicleNumber'],
            'entryTime': record['EntryTime'].isoformat(),
            'parkingDuration': fee_info['duration_display'],
            'fee': fee_info['fee'],
            'lotName': record['LotName']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@kiosk_bp.route('/apply-discount', methods=['POST'])
def apply_discount():
    """
    Apply discount coupon to parking fee
    POST /api/v1/kiosk/apply-discount
    Body: {"recordId": 123, "couponCode": "A1B2C3D4E5F6"}
    """
    try:
        data = request.get_json()
        
        if not data or 'recordId' not in data or 'couponCode' not in data:
            return jsonify({'error': 'recordId and couponCode are required'}), 400
        
        record_id = data['recordId']
        coupon_code = data['couponCode']
        
        # Validate coupon
        validation = CouponService.validate_coupon(coupon_code, record_id)
        
        if not validation['valid']:
            return jsonify({'message': validation['reason']}), 400
        
        # Calculate fee with discount
        try:
            fee_info = BillingService.apply_coupon_discount(record_id, [coupon_code])
            
            return jsonify({
                'originalFee': fee_info['original_fee'],
                'discountAmount': fee_info['total_discount'],
                'finalFee': fee_info['final_fee'],
                'appliedCoupons': [coupon['code'] for coupon in fee_info['applied_coupons']]
            })
            
        except Exception as e:
            return jsonify({'message': f'優惠券應用失敗: {str(e)}'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@kiosk_bp.route('/pay', methods=['POST'])
def process_payment():
    """
    Process payment
    POST /api/v1/kiosk/pay
    Body: {"recordId": 123, "amountPaid": 60, "paymentMethod": "CreditCard", "coupons": ["CODE1"]}
    """
    try:
        data = request.get_json()
        
        required_fields = ['recordId', 'amountPaid', 'paymentMethod']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'recordId, amountPaid, and paymentMethod are required'}), 400
        
        record_id = data['recordId']
        amount_paid = data['amountPaid']
        payment_method = data['paymentMethod']
        applied_coupons = data.get('coupons', [])
        
        # Validate payment method
        if payment_method not in ['Cash', 'CreditCard']:
            return jsonify({'error': 'Invalid payment method. Use Cash or CreditCard'}), 400
        
        # Process payment
        payment_result = BillingService.process_payment(
            record_id, amount_paid, payment_method, applied_coupons
        )
        
        if payment_result['success']:
            return jsonify({
                'message': '繳費成功！請於 15 分鐘內離場。',
                'exitBy': payment_result['exit_deadline'].isoformat(),
                'transactionId': payment_result['transaction_id'],
                'change': payment_result.get('change', 0)
            })
        else:
            return jsonify({'error': 'Payment processing failed'}), 500
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@kiosk_bp.route('/vehicle-status/<plate>', methods=['GET'])
def get_vehicle_status(plate):
    """
    Get current vehicle status for display
    GET /api/v1/kiosk/vehicle-status/ABC-1234
    """
    try:
        query = """
            SELECT pr.*, pl.Name as LotName, pl.HourlyRate
            FROM PARKING_RECORD pr
            JOIN PARKING_LOT pl ON pr.ParkingLotID = pl.ParkingLotID
            WHERE pr.VehicleNumber = %s AND pr.ExitTime IS NULL
            ORDER BY pr.EntryTime DESC
        """
        
        result = db_connector.execute_query(query, (plate,))
        
        if not result:
            return jsonify({'status': 'not_found', 'message': '車輛不在場內'}), 404
        
        record = result[0]
        
        # Check payment status
        if record['PaidUntilTime']:
            from datetime import datetime
            current_time = datetime.now()
            
            if current_time <= record['PaidUntilTime']:
                status = 'paid'
                message = f"已繳費，請於 {record['PaidUntilTime'].strftime('%H:%M')} 前離場"
            else:
                status = 'payment_expired'
                message = '繳費時間已過，需重新繳費'
        else:
            status = 'unpaid'
            message = '尚未繳費'
        
        return jsonify({
            'status': status,
            'message': message,
            'recordId': record['RecordID'],
            'licensePlate': record['VehicleNumber'],
            'entryTime': record['EntryTime'].isoformat(),
            'lotName': record['LotName'],
            'paidUntilTime': record['PaidUntilTime'].isoformat() if record['PaidUntilTime'] else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500