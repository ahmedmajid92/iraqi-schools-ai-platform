"""
Simple authentication service for Iraq Education AI Assistant.
Supports teacher and student roles with bcrypt password hashing.
"""
import os
from typing import Optional, Dict, Tuple
from functools import wraps

from flask import session, redirect, url_for, request, flash

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


def is_auth_available() -> bool:
    """Check if authentication is available."""
    return BCRYPT_AVAILABLE


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    if not BCRYPT_AVAILABLE:
        # Fallback to simple hash (NOT secure - just for demo)
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    if not BCRYPT_AVAILABLE:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == hashed
    
    return bcrypt.checkpw(password.encode(), hashed.encode())


def login_user(user: Dict) -> None:
    """Set user session."""
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user.get('role', 'student')
    session['display_name'] = user.get('display_name') or user['username']
    session['grade'] = user.get('grade') or ''  # Convert None to empty string


def logout_user() -> None:
    """Clear user session."""
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    session.pop('display_name', None)


def get_current_user() -> Optional[Dict]:
    """Get current logged-in user from session."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return {
        'id': user_id,
        'username': session.get('username'),
        'role': session.get('role'),
        'display_name': session.get('display_name')
    }


def is_logged_in() -> bool:
    """Check if user is logged in."""
    return 'user_id' in session


def is_teacher() -> bool:
    """Check if current user is a teacher."""
    return session.get('role') == 'teacher'


def is_student() -> bool:
    """Check if current user is a student."""
    return session.get('role') == 'student'


def login_required(f):
    """Decorator to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('يرجى تسجيل الدخول أولاً', 'warning')
            return redirect(url_for('main.login_page', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    """Decorator to require teacher role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('يرجى تسجيل الدخول أولاً', 'warning')
            return redirect(url_for('main.login_page', next=request.url))
        if not is_teacher():
            flash('هذه الصفحة للأساتذة فقط', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format."""
    if not username:
        return False, "يرجى إدخال اسم المستخدم"
    if len(username) < 3:
        return False, "اسم المستخدم يجب أن يكون 3 أحرف على الأقل"
    if len(username) > 30:
        return False, "اسم المستخدم طويل جداً"
    if not username.replace('_', '').replace('-', '').isalnum():
        return False, "اسم المستخدم يجب أن يحتوي على أحرف وأرقام فقط"
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength."""
    if not password:
        return False, "يرجى إدخال كلمة المرور"
    if len(password) < 6:
        return False, "كلمة المرور يجب أن تكون 6 أحرف على الأقل"
    if len(password) > 100:
        return False, "كلمة المرور طويلة جداً"
    return True, ""
