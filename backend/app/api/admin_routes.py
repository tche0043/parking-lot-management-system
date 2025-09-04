from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
from ..utils.db_connector import db_connector
from ..services.billing_service import BillingService
from ..services.coupon_service import CouponService
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')

# Authentication middleware (simplified for demo)
def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_super_admin(f):
    """Decorator to require super admin privileges"""
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        if session.get('role_level') != 99:
            return jsonify({'error': 'Super admin privileges required'}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_admin_lot_permissions(admin_id):
    """Get parking lots this admin can manage"""
    query = """
        SELECT DISTINCT ala.ParkingLotID
        FROM ADMIN_LOT_ASSIGNMENTS ala
        WHERE ala.AdminID = %s
    """
    result = db_connector.execute_query(query, (admin_id,))
    return [row['ParkingLotID'] for row in result]

@admin_bp.route('/login', methods=['POST'])
def admin_login():
    """
    Admin login
    POST /api/v1/admin/login
    Body: {"username": "admin", "password": "password"}
    """
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password are required'}), 400
        
        username = data['username']
        password = data['password']
        
        # Hash password for comparison (in production, use proper password hashing)
        password_hash = hashlib.sha256(password.encode()).hexdigest().upper()
        
        # Verify credentials
        query = """
            SELECT AdminID, Username, RoleLevel
            FROM ADMINS
            WHERE Username = %s AND PasswordHash = %s
        """
        
        result = db_connector.execute_query(query, (username, password_hash))
        
        if not result:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        admin = result[0]
        
        # Set session
        session['admin_id'] = admin['AdminID']
        session['username'] = admin['Username']
        session['role_level'] = admin['RoleLevel']
        
        # Get assigned parking lots for non-super admins
        assigned_lots = []
        if admin['RoleLevel'] != 99:
            assigned_lots = get_admin_lot_permissions(admin['AdminID'])
        
        return jsonify({
            'success': True,
            'admin': {
                'id': admin['AdminID'],
                'username': admin['Username'],
                'roleLevel': admin['RoleLevel'],
                'roleName': 'Super Admin' if admin['RoleLevel'] == 99 else 'Lot Manager',
                'assignedLots': assigned_lots
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/logout', methods=['POST'])
@require_auth
def admin_logout():
    """Admin logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@admin_bp.route('/profile', methods=['GET'])
@require_auth
def get_admin_profile():
    """Get current admin profile"""
    try:
        admin_id = session['admin_id']
        
        query = """
            SELECT a.AdminID, a.Username, a.RoleLevel,
                   COUNT(ala.ParkingLotID) as AssignedLotsCount
            FROM ADMINS a
            LEFT JOIN ADMIN_LOT_ASSIGNMENTS ala ON a.AdminID = ala.AdminID
            WHERE a.AdminID = %s
            GROUP BY a.AdminID, a.Username, a.RoleLevel
        """
        
        result = db_connector.execute_query(query, (admin_id,))
        
        if result:
            admin = result[0]
            assigned_lots = get_admin_lot_permissions(admin_id) if admin['RoleLevel'] != 99 else []
            
            return jsonify({
                'id': admin['AdminID'],
                'username': admin['Username'],
                'roleLevel': admin['RoleLevel'],
                'roleName': 'Super Admin' if admin['RoleLevel'] == 99 else 'Lot Manager',
                'assignedLotsCount': admin['AssignedLotsCount'],
                'assignedLots': assigned_lots
            })
        else:
            return jsonify({'error': 'Admin not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/lots', methods=['GET'])
@require_auth
def get_parking_lots():
    """Get parking lots (filtered by admin permissions)"""
    try:
        admin_id = session['admin_id']
        role_level = session['role_level']
        
        if role_level == 99:
            # Super admin sees all lots
            query = """
                SELECT pl.*, 
                       (SELECT COUNT(*) FROM PARKING_RECORD pr WHERE pr.ParkingLotID = pl.ParkingLotID AND pr.ExitTime IS NULL) as CurrentOccupancy
                FROM PARKING_LOT pl
                ORDER BY pl.Name
            """
            params = []
        else:
            # Lot manager sees only assigned lots
            query = """
                SELECT pl.*, 
                       (SELECT COUNT(*) FROM PARKING_RECORD pr WHERE pr.ParkingLotID = pl.ParkingLotID AND pr.ExitTime IS NULL) as CurrentOccupancy
                FROM PARKING_LOT pl
                JOIN ADMIN_LOT_ASSIGNMENTS ala ON pl.ParkingLotID = ala.ParkingLotID
                WHERE ala.AdminID = %s
                ORDER BY pl.Name
            """
            params = [admin_id]
        
        result = db_connector.execute_query(query, params)
        
        lots = []
        for lot in result:
            lots.append({
                'id': lot['ParkingLotID'],           # 前端儀表板期望 lot.id
                'ParkingLotID': lot['ParkingLotID'], # 管理員設定頁面期望 lot.ParkingLotID
                'name': lot['Name'],                 # 前端儀表板期望 lot.name
                'Name': lot['Name'],                 # 管理員設定頁面期望 lot.Name
                'address': lot['Address'],
                'totalSpaces': lot['TotalSpaces'],
                'currentOccupancy': lot['CurrentOccupancy'],
                'availableSpaces': lot['TotalSpaces'] - lot['CurrentOccupancy'],
                'hourlyRate': lot['HourlyRate'],
                'dailyMaxRate': lot['DailyMaxRate']
            })
        
        return jsonify({'lots': lots})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/lots', methods=['POST'])
@require_super_admin
def create_parking_lot():
    """
    Create new parking lot (Super Admin only)
    POST /api/v1/admin/lots
    Body: {"name": "New Lot", "address": "123 Main St", "totalSpaces": 100, "hourlyRate": 30, "dailyMaxRate": 200}
    """
    try:
        data = request.get_json()
        
        required_fields = ['name', 'address', 'totalSpaces', 'hourlyRate']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'name, address, totalSpaces, and hourlyRate are required'}), 400
        
        query = """
            INSERT INTO PARKING_LOT (Name, Address, TotalSpaces, HourlyRate, DailyMaxRate)
            OUTPUT INSERTED.ParkingLotID
            VALUES (%s, %s, %s, %s, %s)
        """
        
        result = db_connector.execute_query(query, (
            data['name'],
            data['address'],
            data['totalSpaces'],
            data['hourlyRate'],
            data.get('dailyMaxRate')
        ))
        
        if result:
            lot_id = result[0]['ParkingLotID']
            return jsonify({
                'success': True,
                'lotId': lot_id,
                'message': 'Parking lot created successfully'
            }), 201
        else:
            return jsonify({'error': 'Failed to create parking lot'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/lots/<int:lot_id>/vehicles', methods=['GET'])
@require_auth
def get_lot_vehicles(lot_id):
    """Get vehicles in specific parking lot"""
    try:
        admin_id = session['admin_id']
        role_level = session['role_level']
        
        # Check permissions
        if role_level != 99:
            allowed_lots = get_admin_lot_permissions(admin_id)
            if lot_id not in allowed_lots:
                return jsonify({'error': 'Access denied to this parking lot'}), 403
        
        status = request.args.get('status', 'current')
        
        if status == 'current':
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
        elif status == 'history':
            days = int(request.args.get('days', 7))
            query = """
                SELECT pr.RecordID, pr.VehicleNumber, pr.EntryTime, pr.ExitTime, pr.TotalFee,
                       DATEDIFF(minute, pr.EntryTime, ISNULL(pr.ExitTime, GETDATE())) as DurationMinutes
                FROM PARKING_RECORD pr
                WHERE pr.ParkingLotID = %s 
                  AND pr.EntryTime >= DATEADD(day, -%s, GETDATE())
                ORDER BY pr.EntryTime DESC
            """
            params = [lot_id, days]
        else:
            return jsonify({'error': 'Invalid status parameter'}), 400
        
        result = db_connector.execute_query(query, [lot_id] if status == 'current' else params)
        
        vehicles = []
        for record in result:
            vehicle_data = {
                'recordId': record['RecordID'],
                'licensePlate': record['VehicleNumber'],
                'entryTime': record['EntryTime'].isoformat(),
                'totalFee': record['TotalFee']
            }
            
            if status == 'current':
                # Calculate real-time fee for current vehicles
                try:
                    from ..services.billing_service import BillingService
                    billing_result = BillingService.calculate_parking_fee(record['RecordID'])
                    current_fee = billing_result['fee']
                except Exception as e:
                    current_fee = 0
                    
                vehicle_data.update({
                    'paymentStatus': record['PaymentStatus'],
                    'paidUntilTime': record['PaidUntilTime'].isoformat() if record['PaidUntilTime'] else None,
                    'currentFee': current_fee  # Add real-time calculated fee
                })
            else:
                vehicle_data.update({
                    'exitTime': record['ExitTime'].isoformat() if record['ExitTime'] else None,
                    'durationMinutes': record['DurationMinutes']
                })
            
            vehicles.append(vehicle_data)
        
        return jsonify({
            'lotId': lot_id,
            'status': status,
            'count': len(vehicles),
            'vehicles': vehicles
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/records/<int:record_id>', methods=['PUT'])
@require_auth
def update_parking_record(record_id):
    """
    Update parking record (manual override)
    PUT /api/v1/admin/records/{record_id}
    Body: {"action": "mark_paid", "amount": 100} or {"action": "force_exit"}
    """
    try:
        admin_id = session['admin_id']
        role_level = session['role_level']
        
        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({'error': 'action is required'}), 400
        
        # Get record and check permissions
        record_query = """
            SELECT pr.*, pl.Name as LotName
            FROM PARKING_RECORD pr
            JOIN PARKING_LOT pl ON pr.ParkingLotID = pl.ParkingLotID
            WHERE pr.RecordID = %s
        """
        
        record_result = db_connector.execute_query(record_query, (record_id,))
        
        if not record_result:
            return jsonify({'error': 'Parking record not found'}), 404
        
        record = record_result[0]
        
        # Check lot permission for non-super admins
        if role_level != 99:
            allowed_lots = get_admin_lot_permissions(admin_id)
            if record['ParkingLotID'] not in allowed_lots:
                return jsonify({'error': 'Access denied to this parking lot'}), 403
        
        action = data['action']
        current_time = datetime.now()
        
        if action == 'mark_paid':
            amount = data.get('amount', 0)
            exit_deadline = current_time + timedelta(minutes=15)
            
            # Calculate total fee - if there's already a TotalFee, add to it, otherwise use the new amount
            current_total_fee = record.get('TotalFee', 0) or 0  # Handle NULL values
            new_total_fee = current_total_fee + amount
            
            # Update record
            update_query = """
                UPDATE PARKING_RECORD 
                SET PaidUntilTime = %s, TotalFee = %s
                WHERE RecordID = %s
            """
            db_connector.execute_query(update_query, (exit_deadline, new_total_fee, record_id), fetch=False)
            
            # Insert payment record
            payment_query = """
                INSERT INTO PAYMENT_RECORD (RecordID, PaymentAmount, PaymentMethod, PaymentTime, TransactionID)
                VALUES (%s, %s, %s, %s, %s)
            """
            transaction_id = f"ADMIN{current_time.strftime('%Y%m%d%H%M%S')}{record_id}"
            db_connector.execute_query(payment_query, 
                                     (record_id, amount, 'Manual', current_time, transaction_id), 
                                     fetch=False)
            
            return jsonify({
                'success': True,
                'message': f'Record marked as paid. Total fee: NT${new_total_fee} (added NT${amount})',
                'paidUntilTime': exit_deadline.isoformat(),
                'totalFee': new_total_fee,
                'addedAmount': amount
            })
            
        elif action == 'force_exit':
            update_query = """
                UPDATE PARKING_RECORD 
                SET ExitTime = %s
                WHERE RecordID = %s
            """
            db_connector.execute_query(update_query, (current_time, record_id), fetch=False)
            
            return jsonify({
                'success': True,
                'message': 'Vehicle marked as exited',
                'exitTime': current_time.isoformat()
            })
            
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reports/revenue', methods=['GET'])
@require_auth
def get_revenue_report():
    """
    Get revenue report
    GET /api/v1/admin/reports/revenue%slot_id=1&start_date=2025-01-01&end_date=2025-01-31
    """
    try:
        admin_id = session['admin_id']
        role_level = session['role_level']
        
        lot_id = request.args.get('lot_id', type=int)
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Check lot permission
        if lot_id and role_level != 99:
            allowed_lots = get_admin_lot_permissions(admin_id)
            if lot_id not in allowed_lots:
                return jsonify({'error': 'Access denied to this parking lot'}), 403
        
        # Build query
        base_query = """
            SELECT 
                pl.ParkingLotID,
                pl.Name as LotName,
                COUNT(pr.RecordID) as TotalTransactions,
                COUNT(CASE WHEN pr.ExitTime IS NOT NULL THEN 1 END) as CompletedParking,
                ISNULL(SUM(pr.TotalFee), 0) as TotalRevenue,
                AVG(CAST(pr.TotalFee as FLOAT)) as AverageRevenue
            FROM PARKING_LOT pl
            LEFT JOIN PARKING_RECORD pr ON pl.ParkingLotID = pr.ParkingLotID
                AND CAST(pr.EntryTime AS DATE) BETWEEN %s AND %s
                AND pr.TotalFee IS NOT NULL
        """
        
        params = [start_date, end_date]
        
        if lot_id:
            base_query += " WHERE pl.ParkingLotID = %s"
            params.append(lot_id)
        elif role_level != 99:
            # Non-super admin: filter by assigned lots
            allowed_lots = get_admin_lot_permissions(admin_id)
            if allowed_lots:
                placeholders = ','.join(['%s'] * len(allowed_lots))
                base_query += f" WHERE pl.ParkingLotID IN ({placeholders})"
                params.extend(allowed_lots)
        
        base_query += " GROUP BY pl.ParkingLotID, pl.Name ORDER BY TotalRevenue DESC"
        
        result = db_connector.execute_query(base_query, params)
        
        reports = []
        total_revenue = 0
        
        for row in result:
            total_revenue += row['TotalRevenue']
            reports.append({
                'lotId': row['ParkingLotID'],
                'lotName': row['LotName'],
                'totalTransactions': row['TotalTransactions'],
                'completedParking': row['CompletedParking'],
                'totalRevenue': row['TotalRevenue'],
                'averageRevenue': round(row['AverageRevenue'] or 0, 2)
            })
        
        return jsonify({
            'startDate': start_date,
            'endDate': end_date,
            'totalRevenue': total_revenue,
            'reports': reports
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/dashboard', methods=['GET'])
@require_auth
def get_dashboard_data():
    """Get dashboard summary data"""
    try:
        admin_id = session['admin_id']
        role_level = session['role_level']
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Build base query based on admin permissions
        if role_level == 99:
            # Super admin sees all lots
            lot_filter = ""
            params = []
        else:
            # Lot manager sees only assigned lots
            allowed_lots = get_admin_lot_permissions(admin_id)
            if not allowed_lots:
                return jsonify({
                    'totalLots': 0,
                    'totalSpaces': 0,
                    'currentOccupancy': 0,
                    'todayRevenue': 0,
                    'todayEntries': 0,
                    'lots': []
                })
            
            placeholders = ','.join(['%s'] * len(allowed_lots))
            lot_filter = f"WHERE pl.ParkingLotID IN ({placeholders})"
            params = allowed_lots
        
        # Get basic parking lot statistics
        basic_query = f"""
            SELECT 
                COUNT(pl.ParkingLotID) as TotalLots,
                ISNULL(SUM(pl.TotalSpaces), 0) as TotalSpaces
            FROM PARKING_LOT pl
            {lot_filter}
        """
        basic_result = db_connector.execute_query(basic_query, params)
        basic_stats = basic_result[0] if basic_result else {'TotalLots': 0, 'TotalSpaces': 0}
        
        # Get current occupancy
        occupancy_query = f"""
            SELECT COUNT(*) as CurrentOccupancy
            FROM PARKING_RECORD pr
            JOIN PARKING_LOT pl ON pr.ParkingLotID = pl.ParkingLotID
            WHERE pr.ExitTime IS NULL {lot_filter.replace('WHERE', 'AND') if lot_filter else ''}
        """
        occupancy_result = db_connector.execute_query(occupancy_query, params)
        current_occupancy = occupancy_result[0]['CurrentOccupancy'] if occupancy_result else 0
        
        # Get today's revenue and entries
        today_query = f"""
            SELECT 
                ISNULL(SUM(pr.TotalFee), 0) as TodayRevenue,
                COUNT(*) as TodayEntries
            FROM PARKING_RECORD pr
            JOIN PARKING_LOT pl ON pr.ParkingLotID = pl.ParkingLotID
            WHERE CAST(pr.EntryTime AS DATE) = '{today}' 
            {lot_filter.replace('WHERE', 'AND') if lot_filter else ''}
        """
        today_result = db_connector.execute_query(today_query, params)
        today_stats = today_result[0] if today_result else {'TodayRevenue': 0, 'TodayEntries': 0}
        
        # Combine results
        summary = {
            'TotalLots': basic_stats['TotalLots'],
            'TotalSpaces': basic_stats['TotalSpaces'], 
            'CurrentOccupancy': current_occupancy,
            'TodayRevenue': today_stats['TodayRevenue'],
            'TodayEntries': today_stats['TodayEntries']
        }
        
        return jsonify({
            'totalLots': summary.get('TotalLots', 0),
            'totalSpaces': summary.get('TotalSpaces', 0),
            'currentOccupancy': summary.get('CurrentOccupancy', 0),
            'occupancyRate': round((summary.get('CurrentOccupancy', 0) / max(summary.get('TotalSpaces', 1), 1)) * 100, 1),
            'todayRevenue': summary.get('TodayRevenue', 0),
            'todayEntries': summary.get('TodayEntries', 0)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/generate-coupon', methods=['POST'])
@require_auth
def generate_coupon():
    """
    Generate discount coupon for partner merchants
    POST /api/v1/admin/generate-coupon
    Body: {"parkingLotId": 1, "partnerName": "Starbucks", "quantity": 1}
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '請提供必要參數'}), 400
            
        parking_lot_id = data.get('parkingLotId')
        partner_name = data.get('partnerName', '未知店家')
        quantity = data.get('quantity', 1)
        
        if not parking_lot_id:
            return jsonify({'error': '請指定停車場ID'}), 400
            
        admin_id = session['admin_id']
        role_level = session['role_level']
        
        # Check admin permissions for this parking lot
        if role_level != 99:  # Not super admin
            allowed_lots = get_admin_lot_permissions(admin_id)
            if parking_lot_id not in allowed_lots:
                return jsonify({'error': '無權限為此停車場生成優惠券'}), 403
        
        # Validate parking lot exists
        lot_query = "SELECT Name FROM PARKING_LOT WHERE ParkingLotID = %s"
        lot_result = db_connector.execute_query(lot_query, (parking_lot_id,))
        
        if not lot_result:
            return jsonify({'error': '停車場不存在'}), 404
            
        lot_name = lot_result[0]['Name']
        
        # Generate coupons
        generated_coupons = []
        for i in range(min(quantity, 10)):  # Limit to 10 coupons per request
            coupon_result = CouponService.generate_coupon(parking_lot_id, partner_name)
            
            if coupon_result['success']:
                generated_coupons.append({
                    'code': coupon_result['code'],
                    'discountId': coupon_result['discount_id'],
                    'expiryTime': coupon_result['expiry_time'].isoformat()
                })
        
        if generated_coupons:
            return jsonify({
                'success': True,
                'message': f'成功為 {lot_name} 生成 {len(generated_coupons)} 張優惠券',
                'parkingLotId': parking_lot_id,
                'parkingLotName': lot_name,
                'partnerName': partner_name,
                'coupons': generated_coupons,
                'generatedAt': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': '優惠券生成失敗'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= 管理員管理 API =============

@admin_bp.route('/admins', methods=['GET'])
@require_super_admin
def get_admins():
    """
    Get all administrators (Super Admin only)
    GET /api/v1/admin/admins
    """
    try:
        query = """
            SELECT a.AdminID, a.Username, a.RoleLevel, a.CreatedAt, a.LastLoginAt
            FROM ADMINS a
            ORDER BY a.CreatedAt DESC
        """
        result = db_connector.execute_query(query)
        
        # Get lot assignments for each admin
        admins = []
        for admin in result:
            lot_query = """
                SELECT pl.ParkingLotID, pl.Name
                FROM PARKING_LOT pl
                JOIN ADMIN_LOT_ASSIGNMENTS ala ON pl.ParkingLotID = ala.ParkingLotID
                WHERE ala.AdminID = %s
            """
            lots = db_connector.execute_query(lot_query, (admin['AdminID'],))
            
            admins.append({
                'AdminID': admin['AdminID'],
                'Username': admin['Username'],
                'RoleLevel': admin['RoleLevel'],
                'CreatedAt': admin['CreatedAt'].strftime('%Y-%m-%d %H:%M:%S') if admin['CreatedAt'] is not None else None,
                'LastLoginTime': admin['LastLoginAt'].strftime('%Y-%m-%d %H:%M:%S') if admin['LastLoginAt'] is not None else None,
                'lots': lots
            })
        
        return jsonify(admins)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admins/<int:admin_id>', methods=['GET'])
@require_super_admin
def get_admin(admin_id):
    """
    Get specific administrator details
    GET /api/v1/admin/admins/{admin_id}
    """
    try:
        query = """
            SELECT a.AdminID, a.Username, a.RoleLevel, a.CreatedAt, a.LastLoginAt
            FROM ADMINS a
            WHERE a.AdminID = %s
        """
        result = db_connector.execute_query(query, (admin_id,))
        
        if not result:
            return jsonify({'error': 'Administrator not found'}), 404
        
        admin = result[0]
        
        # Get lot assignments
        lot_query = """
            SELECT pl.ParkingLotID, pl.Name
            FROM PARKING_LOT pl
            JOIN ADMIN_LOT_ASSIGNMENTS ala ON pl.ParkingLotID = ala.ParkingLotID
            WHERE ala.AdminID = %s
        """
        lots = db_connector.execute_query(lot_query, (admin_id,))
        
        # Format the response with proper field names and date formatting
        response_data = {
            'AdminID': admin['AdminID'],
            'Username': admin['Username'],
            'RoleLevel': admin['RoleLevel'],
            'CreatedAt': admin['CreatedAt'].strftime('%Y-%m-%d %H:%M:%S') if admin['CreatedAt'] is not None else None,
            'LastLoginTime': admin['LastLoginAt'].strftime('%Y-%m-%d %H:%M:%S') if admin['LastLoginAt'] is not None else None,
            'lots': lots
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admins', methods=['POST'])
@require_super_admin
def create_admin():
    """
    Create new administrator (Super Admin only)
    POST /api/v1/admin/admins
    Body: {"Username": "admin", "Password": "password", "RoleLevel": 1, "lots": [1, 2]}
    """
    try:
        data = request.get_json()
        
        required_fields = ['Username', 'Password', 'RoleLevel']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Username, Password, and RoleLevel are required'}), 400
        
        username = data['Username'].strip()
        password = data['Password']
        role_level = data['RoleLevel']
        lot_ids = data.get('lots', [])
        
        # Validate role level
        if role_level not in [1, 99]:
            return jsonify({'error': 'RoleLevel must be 1 (LotManager) or 99 (SuperAdmin)'}), 400
        
        # Check if username already exists (case-insensitive)
        check_query = "SELECT AdminID, Username FROM ADMINS WHERE LOWER(Username) = LOWER(%s)"
        existing_conflict = db_connector.execute_query(check_query, (username,))
        if existing_conflict:
            logger.warning(f"Attempted to create duplicate username: {username}, conflicts with existing: {existing_conflict[0]['Username']}")
            return jsonify({'error': f'Username already exists: {username}'}), 400
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Create admin
        insert_query = """
            INSERT INTO ADMINS (Username, PasswordHash, RoleLevel, CreatedAt)
            VALUES (%s, %s, %s, %s)
        """
        db_connector.execute_query(
            insert_query, 
            (username, password_hash, role_level, datetime.now()),
            fetch=False
        )
        
        # Get the newly created admin ID using the username (more reliable)
        id_query = "SELECT AdminID FROM ADMINS WHERE Username = %s"
        result = db_connector.execute_query(id_query, (username,))
        admin_id = result[0]['AdminID'] if result and len(result) > 0 else None
        
        # Assign parking lots (for LotManager)
        if role_level == 1 and lot_ids:
            for lot_id in lot_ids:
                assignment_query = """
                    INSERT INTO ADMIN_LOT_ASSIGNMENTS (AdminID, ParkingLotID, AssignedAt)
                    VALUES (%s, %s, %s)
                """
                db_connector.execute_query(
                    assignment_query, 
                    (admin_id, lot_id, datetime.now()),
                    fetch=False
                )
        
        return jsonify({
            'success': True,
            'message': 'Administrator created successfully',
            'adminId': admin_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admins/<int:admin_id>', methods=['PUT'])
@require_super_admin
def update_admin(admin_id):
    """
    Update administrator (Super Admin only)
    PUT /api/v1/admin/admins/{admin_id}
    Body: {"Username": "admin", "RoleLevel": 1, "lots": [1, 2]}
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Check if admin exists
        check_query = "SELECT AdminID, Username FROM ADMINS WHERE AdminID = %s"
        existing = db_connector.execute_query(check_query, (admin_id,))
        if not existing:
            return jsonify({'error': 'Administrator not found'}), 404
        
        updates = []
        params = []
        
        # Update username if provided
        if 'Username' in data:
            username = data['Username'].strip()
            # Always check for conflicts, even if username seems the same
            conflict_query = "SELECT AdminID, Username FROM ADMINS WHERE LOWER(Username) = LOWER(%s) AND AdminID != %s"
            conflict = db_connector.execute_query(conflict_query, (username, admin_id))
            if conflict:
                return jsonify({'error': f'Username already exists: {conflict[0]["Username"]}'}), 400
            # Always update username to ensure consistency
            updates.append("Username = %s")
            params.append(username)
        
        # Update role level if provided
        if 'RoleLevel' in data:
            role_level = data['RoleLevel']
            if role_level not in [1, 99]:
                return jsonify({'error': 'RoleLevel must be 1 (LotManager) or 99 (SuperAdmin)'}), 400
            updates.append("RoleLevel = %s")
            params.append(role_level)
        
        # Update password if provided
        if 'Password' in data and data['Password']:
            password_hash = hashlib.sha256(data['Password'].encode()).hexdigest()
            updates.append("PasswordHash = %s")
            params.append(password_hash)
        
        # Update admin record
        if updates:
            params.append(admin_id)
            update_query = f"UPDATE ADMINS SET {', '.join(updates)} WHERE AdminID = %s"
            logger.info(f"Updating admin {admin_id} with query: {update_query} and params: {params}")
            result = db_connector.execute_query(update_query, params, fetch=False)
            logger.info(f"Update result: {result} rows affected")
        
        # Update lot assignments
        if 'lots' in data:
            # Remove existing assignments
            delete_query = "DELETE FROM ADMIN_LOT_ASSIGNMENTS WHERE AdminID = %s"
            db_connector.execute_query(delete_query, (admin_id,), fetch=False)
            
            # Add new assignments (for LotManager)
            role_level = data.get('RoleLevel', existing[0].get('RoleLevel', 1))
            if role_level == 1:
                for lot_id in data['lots']:
                    assignment_query = """
                        INSERT INTO ADMIN_LOT_ASSIGNMENTS (AdminID, ParkingLotID, AssignedAt)
                        VALUES (%s, %s, %s)
                    """
                    db_connector.execute_query(
                        assignment_query, 
                        (admin_id, lot_id, datetime.now()),
                        fetch=False
                    )
        
        logger.info(f"Successfully updated admin {admin_id}")
        return jsonify({
            'success': True,
            'message': 'Administrator updated successfully',
            'admin_id': admin_id,
            'updated_fields': len(updates)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admins/<int:admin_id>', methods=['DELETE'])
@require_super_admin
def delete_admin(admin_id):
    """
    Delete administrator (Super Admin only)
    DELETE /api/v1/admin/admins/{admin_id}
    """
    try:
        # Don't allow deleting current admin
        if admin_id == session['admin_id']:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        # Check if admin exists
        check_query = "SELECT AdminID FROM ADMINS WHERE AdminID = %s"
        existing = db_connector.execute_query(check_query, (admin_id,))
        if not existing:
            return jsonify({'error': 'Administrator not found'}), 404
        
        # Delete lot assignments first
        delete_assignments_query = "DELETE FROM ADMIN_LOT_ASSIGNMENTS WHERE AdminID = %s"
        db_connector.execute_query(delete_assignments_query, (admin_id,), fetch=False)
        
        # Delete admin
        delete_query = "DELETE FROM ADMINS WHERE AdminID = %s"
        db_connector.execute_query(delete_query, (admin_id,), fetch=False)
        
        return jsonify({
            'success': True,
            'message': 'Administrator deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500