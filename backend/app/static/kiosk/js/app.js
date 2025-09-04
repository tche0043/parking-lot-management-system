// Parking Payment Kiosk Application

// API Configuration
const API_BASE_URL = window.location.origin;

// Global state
let currentFeeData = null;
let appliedCoupons = [];
let currentPaymentMethod = null;
let autoReturnTimer = null;
let licensePlateInput = '';
let isQRScannerActive = false;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeKiosk();
});

function initializeKiosk() {
    // Start time display
    updateTimeDisplay();
    setInterval(updateTimeDisplay, 1000);
    
    // Bind event listeners
    bindEventListeners();
    
    // Show welcome screen
    showScreen('welcome-screen');
    
    // Initialize virtual keyboard display
    updateLicensePlateDisplay();
}

function bindEventListeners() {
    // 不再需要原有的輸入框事件監聽器
    // 虛擬鍵盤和QR掃描由點擊事件處理
}

// 虛擬鍵盤功能
function inputChar(char) {
    if (licensePlateInput.length < 8) {
        licensePlateInput += char;
        
        // 自動插入破折號
        if (licensePlateInput.length === 3 && !licensePlateInput.includes('-')) {
            // 檢查是否為字母開頭（ABC-1234格式）或數字開頭（123-ABCD格式）
            if (/^[A-Z]{3}$/.test(licensePlateInput) || /^\d{3}$/.test(licensePlateInput)) {
                licensePlateInput += '-';
            }
        }
        
        updateLicensePlateDisplay();
        
        // 添加觸控回饋
        const event = window.event;
        if (event && event.target) {
            event.target.classList.add('shake');
            setTimeout(() => {
                event.target.classList.remove('shake');
            }, 200);
        }
    }
}

function backspace() {
    if (licensePlateInput.length > 0) {
        licensePlateInput = licensePlateInput.slice(0, -1);
        updateLicensePlateDisplay();
    }
}

function clearInput() {
    licensePlateInput = '';
    updateLicensePlateDisplay();
}

function updateLicensePlateDisplay() {
    const display = document.getElementById('license-plate-display');
    if (display) {
        if (licensePlateInput.length === 0) {
            display.textContent = '請點擊下方按鍵輸入車牌號碼';
            display.style.color = '#6c757d';
        } else {
            // 顯示實際輸入的字符（包括用戶手動輸入的 - 符號）
            display.textContent = licensePlateInput;
            display.style.color = '#212529';
        }
    }
}

// QR Modal 控制函數
function openQRModal() {
    const modal = document.getElementById('qr-modal');
    modal.classList.add('show');
    
    // 重置測試按鈕
    const testBtn = document.getElementById('test-coupon-btn');
    if (testBtn) {
        testBtn.style.display = 'inline-flex';
    }
}

function closeQRModal() {
    const modal = document.getElementById('qr-modal');
    modal.classList.remove('show');
    
    // 重置 QR 掃描器狀態
    if (isQRScannerActive) {
        isQRScannerActive = false;
        const scanner = document.getElementById('qr-scanner');
        const text = document.getElementById('qr-scanner-text');
        if (scanner) scanner.classList.remove('active');
        if (text) text.textContent = '點擊此處掃描優惠券QR Code';
    }
}

// QR Code 掃描功能
function startQRScan() {
    const scanner = document.getElementById('qr-scanner');
    const text = document.getElementById('qr-scanner-text');
    
    if (isQRScannerActive) {
        return;
    }
    
    isQRScannerActive = true;
    scanner.classList.add('active');
    text.textContent = '正在啟動相機掃描...';
    
    // 模擬QR掃描過程（實際應用中需要使用相機API）
    setTimeout(() => {
        text.textContent = '請將QR Code對準掃描框';
        
        // 模擬掃描成功（實際應用中由相機掃描結果觸發）
        setTimeout(() => {
            simulateQRScanSuccess();
        }, 3000);
    }, 1000);
}

function simulateQRScanSuccess() {
    // 模擬掃描到12位優惠券代碼
    const mockCouponCode = generateMockCouponCode();
    
    const scanner = document.getElementById('qr-scanner');
    const text = document.getElementById('qr-scanner-text');
    
    scanner.classList.remove('active');
    isQRScannerActive = false;
    
    // 顯示掃描結果
    const result = document.createElement('div');
    result.className = 'qr-result';
    result.innerHTML = `<i class="bi bi-check-circle-fill me-2"></i>掃描成功: ${mockCouponCode}`;
    scanner.appendChild(result);
    
    text.textContent = '掃描完成，優惠券已套用';
    
    // 自動套用優惠券
    setTimeout(() => {
        applyScannedCoupon(mockCouponCode);
    }, 1500);
}

function generateMockCouponCode() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < 12; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

// 測試優惠券功能
function testCoupon() {
    const mockCouponCode = generateMockCouponCode();
    
    // 顯示掃描結果在彈窗中
    const scanner = document.getElementById('qr-scanner');
    const text = document.getElementById('qr-scanner-text');
    
    scanner.classList.add('active');
    text.textContent = '掃描成功! 優惠券: ' + mockCouponCode;
    
    // 2秒後套用優惠券並關閉彈窗
    setTimeout(() => {
        applyScannedCoupon(mockCouponCode);
        closeQRModal();
    }, 2000);
}

function applyScannedCoupon(couponCode) {
    // 重置QR掃描器
    const scanner = document.getElementById('qr-scanner');
    const text = document.getElementById('qr-scanner-text');
    const result = scanner.querySelector('.qr-result');
    
    if (result) {
        result.remove();
    }
    
    text.textContent = '點擊此處掃描優惠券QR Code';
    
    // 套用優惠券邏輯（呼叫現有的 applyCoupon 函數）
    applyCouponByCode(couponCode);
}

// 測試函數已移除 - 生產環境不需要

function updateTimeDisplay() {
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        const now = new Date();
        const timeString = now.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        timeElement.textContent = timeString;
    }
}

function showScreen(screenId) {
    // Reset error screen styling if it was showing paid status
    const errorScreen = document.getElementById('error-screen');
    if (errorScreen && errorScreen.hasAttribute('data-showing-paid-status')) {
        const errorCard = errorScreen.querySelector('.error-card, .success-card');
        const errorIcon = errorScreen.querySelector('.error-icon i');
        const errorTitle = errorScreen.querySelector('.screen-title');
        
        if (errorCard) errorCard.className = 'error-card';
        if (errorIcon) errorIcon.className = 'bi bi-exclamation-circle-fill';
        if (errorTitle) errorTitle.textContent = '系統提示';
        
        errorScreen.removeAttribute('data-showing-paid-status');
    }
    
    // Hide all screens
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    
    // Show target screen
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.classList.add('active');
        
        // Screen-specific actions
        switch (screenId) {
            case 'welcome-screen':
                // Clear previous data
                currentFeeData = null;
                appliedCoupons = [];
                currentPaymentMethod = null;
                licensePlateInput = '';
                isQRScannerActive = false;
                
                // Reset displays
                setTimeout(() => {
                    updateLicensePlateDisplay();
                    // Reset QR scanner
                    const scanner = document.getElementById('qr-scanner');
                    const text = document.getElementById('qr-scanner-text');
                    if (scanner && text) {
                        scanner.classList.remove('active');
                        text.textContent = '點擊此處掃描優惠券QR Code';
                        const result = scanner.querySelector('.qr-result');
                        if (result) {
                            result.remove();
                        }
                    }
                }, 100);
                break;
                
            case 'success-screen':
                // Start auto-return timer
                startAutoReturnTimer();
                break;
        }
    }
}

async function queryFee() {
    const licensePlate = licensePlateInput.trim();
    
    console.log('查詢車牌:', licensePlate); // 調試信息
    
    if (!licensePlate) {
        showError('請輸入車牌號碼');
        return;
    }
    
    if (!validateLicensePlate(licensePlate)) {
        console.log('車牌格式驗證失敗:', licensePlate); // 調試信息
        showError('車牌格式不正確，請輸入正確格式（例如：ABC-1234）');
        return;
    }
    
    try {
        // Show loading state on query button
        const queryButton = document.querySelector('.keyboard-row .keyboard-key.wide[onclick="queryFee()"]');
        let originalText = '查詢';
        if (queryButton) {
            originalText = queryButton.innerHTML;
            queryButton.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 查詢中...';
            queryButton.style.pointerEvents = 'none';
        }
        
        // First check vehicle status
        const statusResponse = await fetch(`${API_BASE_URL}/api/v1/kiosk/vehicle-status/${encodeURIComponent(licensePlate)}`);
        const statusData = await statusResponse.json();
        
        console.log('車輛狀態回應:', statusResponse.status, statusData); // 調試信息
        
        if (statusResponse.ok) {
            // Check payment status
            if (statusData.status === 'paid') {
                // Vehicle is already paid, show status message
                showPaidVehicleStatus(statusData);
                // Restore button
                if (queryButton) {
                    queryButton.innerHTML = originalText;
                    queryButton.style.pointerEvents = 'auto';
                }
                return;
            } else if (statusData.status === 'payment_expired') {
                // Payment has expired, proceed to fee calculation but show different message
                console.log('繳費時間已過，需重新繳費');
            }
        }
        
        // Proceed with fee calculation
        const response = await fetch(`${API_BASE_URL}/api/v1/kiosk/fee?plate=${encodeURIComponent(licensePlate)}`);
        const data = await response.json();
        
        console.log('費用查詢回應:', response.status, data); // 調試信息
        
        if (response.ok) {
            currentFeeData = data;
            appliedCoupons = [];
            displayFeeInfo(data);
            showScreen('fee-screen');
        } else {
            showError(data.message || '查詢失敗，請稍後再試');
        }
        
        // Restore button
        if (queryButton) {
            queryButton.innerHTML = originalText;
            queryButton.style.pointerEvents = 'auto';
        }
    } catch (error) {
        console.error('Fee query error:', error);
        showError('系統連線錯誤，請稍後再試');
        
        // Restore button on error
        const queryButton = document.querySelector('.keyboard-row .keyboard-key.wide[onclick="queryFee()"]');
        if (queryButton) {
            queryButton.innerHTML = '查詢';
            queryButton.style.pointerEvents = 'auto';
        }
    }
}

function validateLicensePlate(plate) {
    // Basic validation for Taiwan license plate format
    const patterns = [
        /^[A-Z]{3}-\d{4}$/,  // ABC-1234
        /^\d{3}-[A-Z]{4}$/,  // 123-ABCD
        /^[A-Z]{2}-\d{4}$/,  // AB-1234
        /^\d{4}-[A-Z]{2}$/   // 1234-AB
    ];
    
    return patterns.some(pattern => pattern.test(plate));
}

function displayFeeInfo(data) {
    document.getElementById('display-license-plate').textContent = data.licensePlate;
    document.getElementById('lot-name').textContent = data.lotName;
    document.getElementById('entry-time').textContent = formatDateTime(data.entryTime);
    document.getElementById('parking-duration').textContent = data.parkingDuration;
    document.getElementById('parking-fee').textContent = `$${data.fee}`;
    
    // Reset amounts
    document.getElementById('original-amount').textContent = `$${data.fee}`;
    document.getElementById('discount-amount').textContent = '-$0';
    document.getElementById('final-fee').textContent = `$${data.fee}`;
    
    // Clear applied coupons (coupon-input no longer exists due to QR scanner)
    const appliedCouponsEl = document.getElementById('applied-coupons');
    if (appliedCouponsEl) {
        appliedCouponsEl.innerHTML = '';
    }
}

// Old manual coupon input function removed - now using QR scanner only

// 由QR掃描觸發的優惠券套用函數
async function applyCouponByCode(couponCode) {
    if (!couponCode) {
        showCouponError('優惠券代碼無效');
        return;
    }
    
    if (couponCode.length !== 12) {
        showCouponError('優惠券代碼必須為12位');
        return;
    }
    
    if (appliedCoupons.includes(couponCode)) {
        showCouponError('此優惠券已經使用過了');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/kiosk/apply-discount`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recordId: currentFeeData.recordId,
                couponCode: couponCode
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Add coupon to applied list
            appliedCoupons.push(couponCode);
            
            // Update fee display
            updateFeeDisplay(data);
            
            // Add coupon tag
            addCouponTag(couponCode);
            
            // Show success feedback
            showCouponSuccess('QR優惠券套用成功！');
        } else {
            showCouponError(data.message || '優惠券無效');
        }
    } catch (error) {
        console.error('QR Coupon application error:', error);
        showCouponError('系統錯誤，請稍後再試');
    }
}

function updateFeeDisplay(data) {
    document.getElementById('original-amount').textContent = `$${data.originalFee}`;
    document.getElementById('discount-amount').textContent = `-$${data.discountAmount}`;
    document.getElementById('final-fee').textContent = `$${data.finalFee}`;
}

function addCouponTag(couponCode) {
    const container = document.getElementById('applied-coupons');
    
    const tag = document.createElement('div');
    tag.className = 'coupon-tag';
    tag.innerHTML = `
        ${couponCode}
        <span class="remove-coupon" onclick="removeCoupon('${couponCode}')">&times;</span>
    `;
    
    container.appendChild(tag);
}

async function removeCoupon(couponCode) {
    // Remove from applied list
    appliedCoupons = appliedCoupons.filter(code => code !== couponCode);
    
    // Remove tag
    const tags = document.querySelectorAll('.coupon-tag');
    tags.forEach(tag => {
        if (tag.textContent.includes(couponCode)) {
            tag.remove();
        }
    });
    
    // Recalculate fee with remaining coupons
    if (appliedCoupons.length > 0) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/kiosk/apply-discount`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    recordId: currentFeeData.recordId,
                    couponCode: appliedCoupons[0] // Apply first remaining coupon
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                updateFeeDisplay(data);
            }
        } catch (error) {
            console.error('Coupon recalculation error:', error);
        }
    } else {
        // Reset to original fee
        const originalFee = currentFeeData.fee;
        document.getElementById('original-amount').textContent = `$${originalFee}`;
        document.getElementById('discount-amount').textContent = '-$0';
        document.getElementById('final-fee').textContent = `$${originalFee}`;
    }
}

function showPaymentScreen() {
    // Get final amount
    const finalAmount = document.getElementById('final-fee').textContent;
    const licensePlate = document.getElementById('display-license-plate').textContent;
    
    // Update payment screen
    document.getElementById('payment-license-plate').textContent = licensePlate;
    document.getElementById('payment-amount').textContent = finalAmount;
    
    // Reset payment method selection
    currentPaymentMethod = null;
    document.querySelectorAll('.payment-method').forEach(method => {
        method.classList.remove('selected');
    });
    
    showScreen('payment-screen');
}

function selectPaymentMethod(method, element) {
    currentPaymentMethod = method;
    
    // Update UI
    document.querySelectorAll('.payment-method').forEach(methodEl => {
        methodEl.classList.remove('selected');
    });
    
    if (element) {
        element.classList.add('selected');
    }
    
    // Auto-proceed to payment after selection
    setTimeout(() => {
        processPayment();
    }, 1000);
}

async function processPayment() {
    if (!currentPaymentMethod) {
        showError('請選擇付款方式');
        return;
    }
    
    // Show processing screen
    document.getElementById('processing-method').textContent = 
        currentPaymentMethod === 'Cash' ? '現金' : '信用卡';
    document.getElementById('processing-amount').textContent = 
        document.getElementById('payment-amount').textContent;
    
    showScreen('processing-screen');
    
    try {
        // Simulate processing delay
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        const finalAmountText = document.getElementById('final-fee').textContent;
        const finalAmount = parseInt(finalAmountText.replace('$', '').replace(',', ''));
        
        const response = await fetch(`${API_BASE_URL}/api/v1/kiosk/pay`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recordId: currentFeeData.recordId,
                amountPaid: finalAmount,
                paymentMethod: currentPaymentMethod,
                coupons: appliedCoupons
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayPaymentSuccess(data);
            showScreen('success-screen');
        } else {
            showError(data.error || '付款失敗，請稍後再試');
        }
    } catch (error) {
        console.error('Payment processing error:', error);
        showError('付款處理失敗，請稍後再試');
    }
}

function displayPaymentSuccess(data) {
    const licensePlate = document.getElementById('display-license-plate').textContent;
    const finalAmount = document.getElementById('final-fee').textContent;
    const paymentMethod = currentPaymentMethod === 'Cash' ? '現金' : '信用卡';
    
    document.getElementById('receipt-license-plate').textContent = licensePlate;
    document.getElementById('receipt-amount').textContent = finalAmount;
    document.getElementById('receipt-method').textContent = paymentMethod;
    document.getElementById('receipt-transaction-id').textContent = data.transactionId;
    document.getElementById('receipt-exit-deadline').textContent = formatDateTime(data.exitBy);
}

function startAutoReturnTimer() {
    let countdown = 5;
    const button = document.querySelector('#success-screen .btn-large');
    
    const updateButton = () => {
        if (countdown > 0) {
            button.innerHTML = `<i class="bi bi-arrow-clockwise me-2"></i>完成 (${countdown}秒後自動返回)`;
            countdown--;
            autoReturnTimer = setTimeout(updateButton, 1000);
        } else {
            startOver();
        }
    };
    
    updateButton();
}

function startOver() {
    if (autoReturnTimer) {
        clearTimeout(autoReturnTimer);
        autoReturnTimer = null;
    }
    
    showScreen('welcome-screen');
}

function goBack() {
    showScreen('welcome-screen');
}

function goBackToFee() {
    showScreen('fee-screen');
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    showScreen('error-screen');
    
    // Add shake animation to error screen
    const errorCard = document.querySelector('#error-screen .error-card');
    if (errorCard) {
        errorCard.classList.add('shake');
        setTimeout(() => {
            errorCard.classList.remove('shake');
        }, 500);
    }
}

function showCouponError(message) {
    // Create temporary error message
    const couponSection = document.querySelector('.coupon-section');
    const existingError = couponSection.querySelector('.coupon-error');
    
    if (existingError) {
        existingError.remove();
    }
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger coupon-error';
    errorDiv.style.marginTop = '1rem';
    errorDiv.textContent = message;
    
    couponSection.appendChild(errorDiv);
    
    // Remove error after 3 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 3000);
    
    // Shake QR scanner instead of coupon input
    const qrScanner = document.getElementById('qr-scanner');
    if (qrScanner) {
        qrScanner.classList.add('shake');
        setTimeout(() => {
            qrScanner.classList.remove('shake');
        }, 500);
    }
}

function showCouponSuccess(message) {
    // Create temporary success message
    const couponSection = document.querySelector('.coupon-section');
    const existingMessage = couponSection.querySelector('.coupon-success');
    
    if (existingMessage) {
        existingMessage.remove();
    }
    
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success coupon-success';
    successDiv.style.marginTop = '1rem';
    successDiv.textContent = message;
    
    couponSection.appendChild(successDiv);
    
    // Remove success message after 2 seconds
    setTimeout(() => {
        successDiv.remove();
    }, 2000);
}

function showPaidVehicleStatus(statusData) {
    // Update error screen to show paid status
    const errorMessage = document.getElementById('error-message');
    const errorScreen = document.getElementById('error-screen');
    const errorCard = errorScreen.querySelector('.error-card');
    const errorIcon = errorCard.querySelector('.error-icon i');
    const errorTitle = errorCard.querySelector('.screen-title');
    
    // Change to success styling
    errorCard.className = 'success-card';
    errorIcon.className = 'bi bi-check-circle-fill';
    errorTitle.textContent = '車輛已繳費';
    
    // Set success message
    errorMessage.innerHTML = `
        <div style="text-align: left; margin-bottom: 1rem;">
            <strong>車牌號碼：</strong>${statusData.licensePlate}<br>
            <strong>停車場：</strong>${statusData.lotName}<br>
            <strong>進場時間：</strong>${formatDateTime(statusData.entryTime)}<br>
            <strong>繳費至：</strong>${formatDateTime(statusData.paidUntilTime)}
        </div>
        <div style="color: #28a745; font-weight: bold; font-size: 1.1em;">
            ${statusData.message}
        </div>
    `;
    
    // Mark this screen as showing paid status for proper cleanup
    errorScreen.setAttribute('data-showing-paid-status', 'true');
    
    showScreen('error-screen');
}

function contactHelp() {
    alert('請洽詢服務台：\n電話：(04) 2123-4567\n或按下緊急求助按鈕');
}

function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Auto-refresh page every 5 minutes to prevent memory leaks
setInterval(() => {
    const currentScreen = document.querySelector('.screen.active');
    if (currentScreen && currentScreen.id === 'welcome-screen') {
        // Only refresh if on welcome screen to avoid interrupting user flow
        location.reload();
    }
}, 5 * 60 * 1000);

// Handle page visibility changes (screen saver mode)
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        // Page became visible again, refresh time
        updateTimeDisplay();
    }
});

// Prevent context menu and text selection for kiosk mode
document.addEventListener('contextmenu', function(e) {
    e.preventDefault();
});

document.addEventListener('selectstart', function(e) {
    e.preventDefault();
});

// Handle keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // ESC key - go back to welcome
    if (e.key === 'Escape') {
        startOver();
    }
    
    // F5 - refresh (allow for maintenance)
    if (e.key === 'F5') {
        return true;
    }
    
    // Disable other function keys
    if (e.key.startsWith('F') && e.key !== 'F5') {
        e.preventDefault();
    }
});

// Error handling for network issues
window.addEventListener('online', function() {
    console.log('Network connection restored');
});

window.addEventListener('offline', function() {
    console.log('Network connection lost');
    showError('網路連線中斷，請檢查網路連線後重試');
});