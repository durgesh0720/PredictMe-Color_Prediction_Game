# 🏦 Withdrawal System Testing Guide

## 🔧 **Test Environment Setup**

### **1. Razorpay Test Mode Configuration**
Add these to your `.env` file:
```bash
# Razorpay Test Credentials
RAZORPAY_KEY_ID=rzp_test_your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
RAZORPAY_ACCOUNT_NUMBER=your_test_account_number
```

### **2. Test Bank Details (For Testing)**
Use these **FAKE** bank details for testing:

**Valid Test Bank Account:**
- **Account Number**: `123456789012`
- **IFSC Code**: `SBIN0001234`
- **Account Holder Name**: `Test User`
- **Bank Name**: `State Bank of India`

**Valid IFSC Code Format:**
- Must be 11 characters
- Format: `ABCD0123456` (4 letters + 0 + 6 alphanumeric)
- Examples: `SBIN0001234`, `HDFC0000123`, `ICIC0001234`

---

## 🧪 **Testing Steps**

### **Step 1: User Withdrawal Request**
1. **Login as a user** with sufficient balance (₹900+)
2. **Go to wallet page**: `/wallet/` or payment dashboard
3. **Fill withdrawal form**:
   - Amount: `100` (or any amount ≤ your balance)
   - Account Number: `123456789012`
   - IFSC Code: `SBIN0001234`
   - Account Holder Name: `Test User`
   - Bank Name: `State Bank of India`
4. **Submit request** - should show success message
5. **Check balance** - should be deducted immediately

### **Step 2: Admin Approval Process**
1. **Login as admin**: `/control-panel/`
2. **Go to withdrawal management**: `/control-panel/withdrawals/`
3. **View pending request** - should show your test request
4. **Click "Approve"** - will trigger Razorpay integration
5. **Check result**:
   - ✅ Success: Request marked as approved
   - ❌ Error: Check Razorpay test credentials

### **Step 3: Admin Rejection Process**
1. **Create another withdrawal request** (repeat Step 1)
2. **In admin panel**, click "Reject" on the request
3. **Provide rejection reason**: "Test rejection"
4. **Submit rejection**
5. **Check result**:
   - User balance should be refunded
   - Request marked as rejected

---

## 🔍 **Common Issues & Solutions**

### **Issue 1: "Insufficient balance. Available: ₹900"**
**Solution**: Make sure withdrawal amount is less than available balance

### **Issue 2: "IFSC code must be 11 characters"**
**Solution**: Use correct format like `SBIN0001234` (exactly 11 characters)

### **Issue 3: "Account number must be 9-18 digits"**
**Solution**: Use numbers only, 9-18 digits (e.g., `123456789012`)

### **Issue 4: "Razorpay error" in admin approval**
**Solutions**:
- Check Razorpay test credentials in `.env`
- Ensure Razorpay account has payout feature enabled
- Verify account number setting is correct

---

## 📋 **Test Scenarios**

### **✅ Valid Test Cases**
1. **Normal withdrawal**: ₹100 with valid bank details
2. **Maximum amount**: Test with max withdrawal limit
3. **Minimum amount**: Test with ₹20 (minimum)
4. **Admin approval**: Test Razorpay integration
5. **Admin rejection**: Test refund functionality

### **❌ Invalid Test Cases**
1. **Insufficient balance**: Try withdrawing more than available
2. **Invalid IFSC**: Use wrong format like `SBIN123` (too short)
3. **Invalid account**: Use letters in account number
4. **Empty fields**: Leave required fields blank
5. **Below minimum**: Try withdrawing ₹10 (below ₹20 minimum)

---

## 🎯 **Expected Results**

### **Successful Withdrawal Request**
- ✅ Amount deducted from user wallet immediately
- ✅ Request appears in admin panel as "Pending"
- ✅ User sees confirmation message

### **Successful Admin Approval**
- ✅ Request status changes to "Approved"
- ✅ Razorpay payout initiated (in test mode)
- ✅ Master wallet debited
- ✅ Transaction logged

### **Successful Admin Rejection**
- ✅ Request status changes to "Rejected"
- ✅ Amount refunded to user wallet
- ✅ Rejection reason recorded

---

## 🔧 **Troubleshooting**

### **Check Logs**
- Django logs for validation errors
- Browser console for JavaScript errors
- Razorpay dashboard for payout status

### **Verify Settings**
- Currency symbols showing ₹ (not $)
- IFSC validation working correctly
- Admin panel accessible at `/control-panel/withdrawals/`

### **Test Mode Verification**
- Razorpay in test mode (no real money transferred)
- Test bank details accepted
- All validations working correctly

---

## 🚀 **Production Checklist**

Before going live:
- [ ] Replace test Razorpay credentials with live ones
- [ ] Update minimum/maximum withdrawal limits
- [ ] Test with real bank account details
- [ ] Verify Razorpay payout feature is enabled
- [ ] Set up proper webhook handling
- [ ] Configure email notifications
- [ ] Test admin approval workflow
- [ ] Verify master wallet integration

---

**🎉 The withdrawal system is now ready for testing!**

Use the test bank details above and follow the testing steps to verify everything works correctly.
