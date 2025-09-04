from flask import Blueprint, request, jsonify
from datetime import datetime
from ..utils.db_connector import db_connector

hardware_bp = Blueprint('hardware', __name__, url_prefix='/api/v1/lots')

@hardware_bp.route('/<int:lot_id>/entry', methods=['POST'])
def vehicle_entry(lot_id):
    """
    Simulate vehicle entry (license plate recognition)
    POST /api/v1/lots/{lot_id}/entry
    Body: {"license_plate": "XYZ-7890"}
    """
    try:
        data = request.get_json()
        
        if not data or 'license_plate' not in data:
            return jsonify({'error': 'license_plate is required'}), 400
        
        license_plate = data['license_plate'].strip().upper()
        
        # Validate parking lot exists
        lot_query = "SELECT Name FROM PARKING_LOT WHERE ParkingLotID = %s"
        lot_result = db_connector.execute_query(lot_query, (lot_id,))
        
        if not lot_result:
            return jsonify({'error': 'Parking lot not found'}), 404
        
        lot_name = lot_result[0]['Name']
        
        # Check if vehicle is already in the lot (no exit record)
        existing_query = """
            SELECT RecordID FROM PARKING_RECORD 
            WHERE VehicleNumber = %s AND ParkingLotID = %s AND ExitTime IS NULL
        """
        existing_result = db_connector.execute_query(existing_query, (license_plate, lot_id))
        
        if existing_result:
            return jsonify({
                'error': f'Vehicle {license_plate} is already in the parking lot',
                'existing_record_id': existing_result[0]['RecordID']
            }), 409
        
        # Create new parking record
        entry_time = datetime.now()
        insert_query = """
            INSERT INTO PARKING_RECORD (ParkingLotID, VehicleNumber, EntryTime)
            OUTPUT INSERTED.RecordID
            VALUES (%s, %s, %s)
        """
        
        result = db_connector.execute_query(insert_query, (lot_id, license_plate, entry_time))
        
        if result:
            record_id = result[0]['RecordID']
            
            return jsonify({
                'recordId': record_id,
                'message': f'車輛 {license_plate} 已於 {entry_time.strftime("%Y-%m-%d %H:%M:%S")} 進入 {lot_name}。',
                'licensePlate': license_plate,
                'lotId': lot_id,
                'lotName': lot_name,
                'entryTime': entry_time.isoformat()
            }), 201
        else:
            return jsonify({'error': 'Failed to create parking record'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hardware_bp.route('/<int:lot_id>/exit', methods=['POST'])
def vehicle_exit(lot_id):
    """
    Simulate vehicle exit (gate control)
    POST /api/v1/lots/{lot_id}/exit
    Body: {"license_plate": "ABC-1234"}
    """
    try:
        data = request.get_json()
        
        if not data or 'license_plate' not in data:
            return jsonify({'error': 'license_plate is required'}), 400
        
        license_plate = data['license_plate'].strip().upper()
        
        # Find active parking record
        query = """
            SELECT pr.*, pl.Name as LotName
            FROM PARKING_RECORD pr
            JOIN PARKING_LOT pl ON pr.ParkingLotID = pl.ParkingLotID
            WHERE pr.VehicleNumber = %s AND pr.ParkingLotID = %s AND pr.ExitTime IS NULL
        """
        
        result = db_connector.execute_query(query, (license_plate, lot_id))
        
        if not result:
            return jsonify({
                'action': 'keep_gate_closed',
                'message': '找不到車輛進場記錄或車輛已離場。'
            }), 404
        
        record = result[0]
        current_time = datetime.now()
        
        # Check payment status
        if record['PaidUntilTime'] is None:
            # Not paid
            return jsonify({
                'action': 'keep_gate_closed',
                'message': '車輛尚未繳費，請先至繳費機繳費。',
                'recordId': record['RecordID']
            }), 402
        
        elif current_time > record['PaidUntilTime']:
            # Payment expired
            return jsonify({
                'action': 'keep_gate_closed',
                'message': '繳費時間已過期，請重新繳費。',
                'recordId': record['RecordID']
            }), 402
        
        else:
            # Payment valid, allow exit
            # Update exit time
            update_query = """
                UPDATE PARKING_RECORD 
                SET ExitTime = %s
                WHERE RecordID = %s
            """
            
            db_connector.execute_query(update_query, (current_time, record['RecordID']), fetch=False)
            
            return jsonify({
                'action': 'open_gate',
                'message': '允許離場，感謝使用。',
                'recordId': record['RecordID'],
                'exitTime': current_time.isoformat()
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hardware_bp.route('/<int:lot_id>/status', methods=['GET'])
def get_lot_status(lot_id):
    """
    Get parking lot current status
    GET /api/v1/lots/{lot_id}/status
    """
    try:
        # Get lot information
        lot_query = """
            SELECT pl.*, 
                   (SELECT COUNT(*) FROM PARKING_RECORD pr WHERE pr.ParkingLotID = pl.ParkingLotID AND pr.ExitTime IS NULL) as CurrentOccupancy
            FROM PARKING_LOT pl
            WHERE pl.ParkingLotID = %s
        """
        
        lot_result = db_connector.execute_query(lot_query, (lot_id,))
        
        if not lot_result:
            return jsonify({'error': 'Parking lot not found'}), 404
        
        lot_info = lot_result[0]
        
        # Get today's statistics
        today_query = """
            SELECT 
                COUNT(*) as TotalEntries,
                COUNT(CASE WHEN pr.ExitTime IS NOT NULL THEN 1 END) as TotalExits,
                ISNULL(SUM(pr.TotalFee), 0) as TotalRevenue
            FROM PARKING_RECORD pr
            WHERE pr.ParkingLotID = %s 
              AND CAST(pr.EntryTime AS DATE) = CAST(GETDATE() AS DATE)
        """
        
        today_result = db_connector.execute_query(today_query, (lot_id,))
        today_stats = today_result[0] if today_result else {}
        
        return jsonify({
            'lotId': lot_info['ParkingLotID'],
            'name': lot_info['Name'],
            'address': lot_info['Address'],
            'totalSpaces': lot_info['TotalSpaces'],
            'currentOccupancy': lot_info['CurrentOccupancy'],
            'availableSpaces': lot_info['TotalSpaces'] - lot_info['CurrentOccupancy'],
            'occupancyRate': round((lot_info['CurrentOccupancy'] / lot_info['TotalSpaces']) * 100, 1),
            'hourlyRate': lot_info['HourlyRate'],
            'dailyMaxRate': lot_info['DailyMaxRate'],
            'todayStats': {
                'totalEntries': today_stats.get('TotalEntries', 0),
                'totalExits': today_stats.get('TotalExits', 0),
                'totalRevenue': today_stats.get('TotalRevenue', 0)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hardware_bp.route('/<int:lot_id>/vehicles', methods=['GET'])
def get_current_vehicles(lot_id):
    """
    Get list of currently parked vehicles
    GET /api/v1/lots/{lot_id}/vehicles%sstatus=parked
    """
    try:
        status = request.args.get('status', 'parked')
        
        if status == 'parked':
            query = """
                SELECT pr.RecordID, pr.VehicleNumber, pr.EntryTime, pr.PaidUntilTime, pr.TotalFee,
                       CASE 
                           WHEN pr.PaidUntilTime IS NULL THEN 'Unpaid'
                           WHEN pr.PaidUntilTime > GETDATE() THEN 'Paid'
                           ELSE 'Payment Expired'
                       END as PaymentStatus
                FROM PARKING_RECORD pr
                WHERE pr.ParkingLotID = %s AND pr.ExitTime IS NULL
                ORDER BY pr.EntryTime DESC
            """
        else:
            return jsonify({'error': 'Invalid status parameter'}), 400
        
        result = db_connector.execute_query(query, (lot_id,))
        
        vehicles = []
        for record in result:
            vehicles.append({
                'recordId': record['RecordID'],
                'licensePlate': record['VehicleNumber'],
                'entryTime': record['EntryTime'].isoformat(),
                'paymentStatus': record['PaymentStatus'],
                'paidUntilTime': record['PaidUntilTime'].isoformat() if record['PaidUntilTime'] else None,
                'totalFee': record['TotalFee']
            })
        
        return jsonify({
            'lotId': lot_id,
            'status': status,
            'count': len(vehicles),
            'vehicles': vehicles
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hardware_bp.route('/<int:lot_id>/generate-coupon', methods=['POST'])
def generate_coupon(lot_id):
    """
    Generate discount coupon for a parking lot (for partners)
    POST /api/v1/lots/{lot_id}/generate-coupon
    Body: {"partner_name": "Coffee Shop A"}
    """
    try:
        from ..services.coupon_service import CouponService
        
        data = request.get_json() or {}
        partner_name = data.get('partner_name', 'Anonymous Partner')
        
        # Validate parking lot exists
        lot_query = "SELECT Name FROM PARKING_LOT WHERE ParkingLotID = %s"
        lot_result = db_connector.execute_query(lot_query, (lot_id,))
        
        if not lot_result:
            return jsonify({'error': 'Parking lot not found'}), 404
        
        # Generate coupon
        coupon_result = CouponService.generate_coupon(lot_id, partner_name)
        
        if coupon_result['success']:
            return jsonify({
                'success': True,
                'message': '優惠券生成成功',
                'coupon': {
                    'code': coupon_result['code'],
                    'parkingLotId': coupon_result['parking_lot_id'],
                    'partnerName': coupon_result['partner_name'],
                    'generatedTime': coupon_result['generated_time'].isoformat(),
                    'expiryTime': coupon_result['expiry_time'].isoformat(),
                    'validFor': '1 小時停車費折抵'
                }
            }), 201
        else:
            return jsonify({'error': 'Failed to generate coupon'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500