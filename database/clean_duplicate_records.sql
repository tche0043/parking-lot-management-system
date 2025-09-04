-- 清理重複車牌記錄的安全腳本

USE ParkingLot;
GO

-- 1. 詳細檢查重複記錄
PRINT '=== 檢查 XYZ-9999 重複記錄詳情 ===';
SELECT
    RecordID as 記錄ID,
    VehicleNumber as 車牌,
    ParkingLotID as 停車場ID,
    EntryTime as 進入時間,
    ExitTime as 離場時間,
    TotalFee as 總費用,
    CreatedAt as 建立時間,
    UpdatedAt as 更新時間,
    DATEDIFF(HOUR, EntryTime, GETDATE()) as 已停車小時數
FROM PARKING_RECORD
WHERE VehicleNumber = 'XYZ-9999'
    AND ParkingLotID = 1
    AND ExitTime IS NULL
ORDER BY EntryTime ASC;

-- 2. 檢查是否有相關的付款記錄
PRINT '=== 檢查相關付款記錄 ===';
SELECT
    pr.RecordID,
    pr.PaymentID,
    pr.PaymentAmount,
    pr.PaymentMethod,
    pr.PaymentTime,
    pr.TransactionID
FROM PAYMENT_RECORD pr
WHERE pr.RecordID IN (7, 1005);

-- 3. 檢查是否有相關的優惠券使用記錄
PRINT '=== 檢查相關優惠券記錄 ===';
SELECT
    d.DiscountID,
    d.Code,
    d.RecordID,
    d.UsedTime,
    d.GeneratedTime
FROM DISCOUNT d
WHERE d.RecordID IN (7, 1005);

-- 4. 安全刪除較新的記錄（保留較舊的記錄）
-- 假設 RecordID 7 是較舊的，1005 是較新的
PRINT '=== 準備刪除較新的記錄 ===';

-- 4a. 先處理外鍵約束 - 刪除相關的付款記錄
BEGIN TRY
    DELETE FROM PAYMENT_RECORD WHERE RecordID = 1005;
    PRINT '✅ 已刪除 RecordID 1005 相關的付款記錄';
END TRY
BEGIN CATCH
    PRINT '⚠️ 刪除付款記錄時發生錯誤: ' + ERROR_MESSAGE();
END CATCH;

-- 4b. 處理相關的優惠券記錄（將 RecordID 設為 NULL）
BEGIN TRY
    UPDATE DISCOUNT 
    SET RecordID = NULL, UsedTime = NULL 
    WHERE RecordID = 1005;
    PRINT '✅ 已清理 RecordID 1005 相關的優惠券記錄';
END TRY
BEGIN CATCH
    PRINT '⚠️ 清理優惠券記錄時發生錯誤: ' + ERROR_MESSAGE();
END CATCH;

-- 4c. 最後刪除重複的停車記錄
BEGIN TRY
    DELETE FROM PARKING_RECORD WHERE RecordID = 1005;
    PRINT '✅ 已成功刪除重複記錄 RecordID 1005';
END TRY
BEGIN CATCH
    PRINT '❌ 刪除停車記錄時發生錯誤: ' + ERROR_MESSAGE();
    PRINT '可能仍有其他外鍵約束阻止刪除';
END CATCH;

-- 5. 驗證清理結果
PRINT '=== 清理後驗證 ===';
SELECT
    RecordID,
    VehicleNumber,
    ParkingLotID,
    EntryTime,
    '剩餘記錄' as 狀態
FROM PARKING_RECORD
WHERE VehicleNumber = 'XYZ-9999'
    AND ParkingLotID = 1
    AND ExitTime IS NULL;

-- 檢查整體重複狀況
PRINT '=== 整體重複狀況檢查 ===';
SELECT
    VehicleNumber,
    ParkingLotID,
    COUNT(*) as 記錄數量
FROM PARKING_RECORD
WHERE ExitTime IS NULL
GROUP BY VehicleNumber, ParkingLotID
HAVING COUNT(*) > 1;

PRINT '=== 清理完成 ===';
PRINT '建議：清理完成後，執行 fix_trigger_v2.sql 建立防重複機制';