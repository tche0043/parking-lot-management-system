import string
import random
from datetime import datetime, timedelta
from ..utils.db_connector import db_connector

class CouponService:
    """Service for managing parking discount coupons"""
    
    @staticmethod
    def generate_coupon(parking_lot_id, partner_name=None):
        """
        Generate a new discount coupon for a specific parking lot
        
        Args:
            parking_lot_id: ID of the parking lot
            partner_name: Optional name of partner generating the coupon
            
        Returns:
            dict: Generated coupon information
        """
        try:
            # Generate 12-character random code
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            
            current_time = datetime.now()
            expiry_time = current_time + timedelta(hours=2)  # 2-hour validity
            
            # Insert coupon into database  
            query = """
                INSERT INTO DISCOUNT (Code, ParkingLotID, GeneratedTime, ExpiryTime, PartnerName)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            result = db_connector.execute_query(query, (code, parking_lot_id, current_time, expiry_time, partner_name), fetch=False)
            
            if result >= 0:  # Insert successful
                # Get the generated discount ID
                id_query = "SELECT DiscountID FROM DISCOUNT WHERE Code = %s"
                id_result = db_connector.execute_query(id_query, (code,))
                
                if id_result:
                    discount_id = id_result[0]['DiscountID']
                else:
                    discount_id = None
                
                return {
                    'success': True,
                    'discount_id': discount_id,
                    'code': code,
                    'parking_lot_id': parking_lot_id,
                    'generated_time': current_time,
                    'expiry_time': expiry_time,
                    'partner_name': partner_name
                }
            else:
                raise Exception("Failed to generate coupon")
                
        except Exception as e:
            raise Exception(f"Coupon generation error: {str(e)}")
    
    @staticmethod
    def validate_coupon(coupon_code, record_id):
        """
        Validate a coupon against all required criteria
        
        Args:
            coupon_code: The coupon code to validate
            record_id: The parking record ID to validate against
            
        Returns:
            dict: Validation result with details
        """
        try:
            # Get coupon information
            coupon_query = """
                SELECT d.*, pl.Name as LotName
                FROM DISCOUNT d
                JOIN PARKING_LOT pl ON d.ParkingLotID = pl.ParkingLotID
                WHERE d.Code = %s
            """
            coupon_result = db_connector.execute_query(coupon_query, (coupon_code,))
            
            if not coupon_result:
                return {'valid': False, 'reason': '優惠券代碼不存在'}
            
            coupon = coupon_result[0]
            
            # Check if already used
            if coupon['UsedTime'] is not None:
                return {'valid': False, 'reason': '優惠券已被使用'}
            
            # Check if expired
            current_time = datetime.now()
            if current_time > coupon['ExpiryTime']:
                return {'valid': False, 'reason': '優惠券已過期'}
            
            # Get parking record information
            record_query = """
                SELECT ParkingLotID, VehicleNumber
                FROM PARKING_RECORD
                WHERE RecordID = %s
            """
            record_result = db_connector.execute_query(record_query, (record_id,))
            
            if not record_result:
                return {'valid': False, 'reason': '停車記錄不存在'}
            
            record = record_result[0]
            
            # Check if coupon is for the same parking lot
            if coupon['ParkingLotID'] != record['ParkingLotID']:
                return {'valid': False, 'reason': '優惠券不適用於此停車場'}
            
            return {
                'valid': True,
                'coupon': coupon,
                'record': record,
                'discount_amount': None  # Will be calculated during application
            }
            
        except Exception as e:
            return {'valid': False, 'reason': f'驗證錯誤: {str(e)}'}
    
    @staticmethod
    def use_coupon(coupon_code, record_id):
        """
        Mark a coupon as used
        
        Args:
            coupon_code: The coupon code to mark as used
            record_id: The parking record ID
            
        Returns:
            bool: Success status
        """
        try:
            current_time = datetime.now()
            
            # Update coupon as used
            query = """
                UPDATE DISCOUNT 
                SET UsedTime = %s, RecordID = %s
                WHERE Code = %s AND UsedTime IS NULL
            """
            
            affected_rows = db_connector.execute_query(query, (current_time, record_id, coupon_code), fetch=False)
            
            if affected_rows > 0:
                return True
            else:
                raise Exception("Coupon could not be marked as used")
                
        except Exception as e:
            raise Exception(f"Coupon usage error: {str(e)}")
    
    @staticmethod
    def get_coupon_history(parking_lot_id=None, days=30):
        """
        Get coupon generation and usage history
        
        Args:
            parking_lot_id: Optional filter by parking lot
            days: Number of days to look back
            
        Returns:
            list: Coupon history records
        """
        try:
            base_query = """
                SELECT d.*, pl.Name as LotName,
                       CASE WHEN d.UsedTime IS NOT NULL THEN 'Used'
                            WHEN d.ExpiryTime < GETDATE() THEN 'Expired'
                            ELSE 'Active' END as Status
                FROM DISCOUNT d
                JOIN PARKING_LOT pl ON d.ParkingLotID = pl.ParkingLotID
                WHERE d.GeneratedTime >= DATEADD(day, -%s, GETDATE())
            """
            
            params = [days]
            
            if parking_lot_id:
                base_query += " AND d.ParkingLotID = %s"
                params.append(parking_lot_id)
            
            base_query += " ORDER BY d.GeneratedTime DESC"
            
            return db_connector.execute_query(base_query, params)
            
        except Exception as e:
            raise Exception(f"Coupon history error: {str(e)}")
    
    @staticmethod
    def cleanup_expired_coupons():
        """
        Clean up expired and old used coupons (for scheduled tasks)
        
        Returns:
            dict: Cleanup statistics
        """
        try:
            # Delete expired unused coupons
            expired_query = """
                DELETE FROM DISCOUNT 
                WHERE UsedTime IS NULL AND ExpiryTime < GETDATE()
            """
            expired_count = db_connector.execute_query(expired_query, fetch=False)
            
            # Delete old used coupons (older than 24 hours)
            old_used_query = """
                DELETE FROM DISCOUNT 
                WHERE UsedTime IS NOT NULL AND UsedTime < DATEADD(hour, -24, GETDATE())
            """
            old_used_count = db_connector.execute_query(old_used_query, fetch=False)
            
            return {
                'expired_coupons_deleted': expired_count,
                'old_used_coupons_deleted': old_used_count,
                'cleanup_time': datetime.now()
            }
            
        except Exception as e:
            raise Exception(f"Coupon cleanup error: {str(e)}")