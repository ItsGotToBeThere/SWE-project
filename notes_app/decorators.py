from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from functools import wraps 

# making the access to librarians only
def librarian_required(view_func):
    @wraps(view_func) 
    def wrapper(request, *args, **kwargs):
        if request.user.groups.filter(name='Librarians').exists():
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied 
    return login_required(wrapper)

# making access to patrons and librarians
def patron_required(view_func):
    @wraps(view_func) 
    def wrapper(request, *args, **kwargs):
        if request.user.groups.filter(name='Patrons').exists() or request.user.groups.filter(name='Librarians').exists():
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied 
    return login_required(wrapper) 
