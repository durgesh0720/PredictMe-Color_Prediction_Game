# User Authentication System - Testing Guide

## 🧪 How to Test the New Authentication System

### Prerequisites
1. Server should be running: `python manage.py runserver`
2. Database migrations applied: `python manage.py migrate`
3. Browser open to: `http://127.0.0.1:8000/`

## 📝 Test Scenarios

### 1. New User Registration
**Steps:**
1. Go to `http://127.0.0.1:8000/`
2. Click "📝 Create Account" button
3. Fill out the registration form:
   - Username: `testuser123`
   - Email: `test@example.com`
   - First Name: `Test`
   - Last Name: `User`
   - Phone: `+1234567890` (optional)
   - Password: `securepass123`
   - Confirm Password: `securepass123`
4. Click "🚀 Create Account"

**Expected Result:**
- User is created and automatically logged in
- Redirected to profile page
- Welcome message displayed
- Starting balance of ₹1000

### 2. User Login
**Steps:**
1. Go to `http://127.0.0.1:8000/login/`
2. Enter credentials:
   - Username/Email: `test@example.com` or `testuser123`
   - Password: `securepass123`
3. Click "🚀 Sign In"

**Expected Result:**
- User is logged in
- Redirected to profile or intended page
- Welcome message displayed

### 3. Profile Management
**Steps:**
1. Login as a user
2. Go to `http://127.0.0.1:8000/profile/`
3. Click "✏️ Edit Profile"
4. Update information:
   - Add bio: "I love playing color prediction games!"
   - Update phone number
   - Set date of birth
5. Upload an avatar image
6. Click "💾 Save Changes"

**Expected Result:**
- Profile information updated
- Avatar displayed
- Success notification shown

### 4. Password Change
**Steps:**
1. From profile page, click "🔒 Change Password"
2. Enter:
   - Current Password: `securepass123`
   - New Password: `newsecurepass456`
   - Confirm Password: `newsecurepass456`
3. Click "🔐 Update Password"

**Expected Result:**
- Password updated successfully
- Success notification shown
- Can login with new password

### 5. Game Room Access
**Steps:**
1. Login as a user
2. Go to home page `http://127.0.0.1:8000/`
3. Select a game room from dropdown
4. Click "🚀 Join Game Room"

**Expected Result:**
- Redirected to game room
- User balance and info displayed
- Can place bets and play game

### 6. Game Room Functionality
**Steps:**
1. Login as a user
2. Join a game room from the home page
3. Try to interact with the game interface

**Expected Result:**
- Game loads properly with responsive design
- Real-time updates work correctly
- Can place bets normally
- Mobile-responsive interface works on all devices

### 7. Logout
**Steps:**
1. From any authenticated page
2. Click "🚪 Logout" button

**Expected Result:**
- User is logged out
- Session cleared
- Redirected to home page
- Logout success message shown

## 🔍 Testing Existing Users

### For Users Created Before Authentication Update
**Steps:**
1. Try to login with existing username
2. Use password: `changeme123` (default password)
3. Go to profile and change password immediately

**Expected Result:**
- Can login with default password
- Should change password for security
- All game data preserved

## 🚨 Error Testing

### 1. Invalid Registration
**Test Cases:**
- Duplicate username/email
- Weak password (less than 8 chars)
- Mismatched password confirmation
- Invalid email format
- Invalid phone number format

**Expected Result:**
- Clear error messages displayed
- Form data preserved
- No JavaScript alerts

### 2. Invalid Login
**Test Cases:**
- Wrong password
- Non-existent user
- Empty fields

**Expected Result:**
- Error message displayed
- No JavaScript alerts
- Form remains accessible

### 3. Unauthorized Access
**Test Cases:**
- Access `/profile/` without login
- Access `/room/main/` without login
- Access protected pages

**Expected Result:**
- Redirected to login page
- Warning message about login requirement
- Can return to intended page after login

## 🎮 Game Functionality Testing

### 1. Betting System
**Steps:**
1. Login and join a game room
2. Place various bets
3. Check balance updates

**Expected Result:**
- Bets processed correctly
- Balance updated in real-time
- No JavaScript prompts

### 2. WebSocket Connection
**Steps:**
1. Login and join game room
2. Open browser developer tools
3. Check WebSocket connection

**Expected Result:**
- WebSocket connects successfully
- Real-time updates work
- User identified correctly

## 📱 Mobile Testing

### 1. Responsive Design
**Steps:**
1. Open site on mobile device or use browser dev tools
2. Test all authentication flows
3. Test game functionality

**Expected Result:**
- All forms work on mobile
- Touch-friendly interface
- No horizontal scrolling
- Readable text and buttons

### 2. Touch Interactions
**Steps:**
1. Test form inputs on mobile
2. Test button clicks
3. Test navigation

**Expected Result:**
- Smooth touch interactions
- Proper keyboard display
- Easy navigation

## 🔧 Admin Panel Testing

### 1. Admin Authentication
**Steps:**
1. Go to `http://127.0.0.1:8000/control-panel/`
2. Login with admin credentials
3. Test dangerous actions (user management, etc.)

**Expected Result:**
- Modal confirmations instead of browser confirms
- Toast notifications instead of alerts
- Smooth admin experience

## ✅ Success Criteria

The authentication system is working correctly if:
- ✅ No JavaScript `prompt()`, `alert()`, or `confirm()` dialogs appear
- ✅ Users can register, login, and logout smoothly
- ✅ Profile management works completely
- ✅ Game functionality is preserved
- ✅ Mobile experience is optimal
- ✅ Security measures are in place
- ✅ Error handling is user-friendly
- ✅ Performance is good

## 🐛 Common Issues and Solutions

### Issue: "Email already exists" during registration
**Solution:** Use a different email address or login with existing account

### Issue: Can't login with old username
**Solution:** Use default password `changeme123` and change it immediately

### Issue: JavaScript errors in console
**Solution:** Check browser console for specific errors and report them

### Issue: Mobile layout issues
**Solution:** Clear browser cache and test again

### Issue: WebSocket connection fails
**Solution:** Ensure Redis server is running for WebSocket functionality

## 📞 Support

If you encounter any issues during testing:
1. Check browser console for JavaScript errors
2. Check server logs for Python errors
3. Verify all migrations are applied
4. Ensure Redis server is running (for WebSockets)
5. Clear browser cache and cookies

The authentication system is now ready for production use! 🎉
