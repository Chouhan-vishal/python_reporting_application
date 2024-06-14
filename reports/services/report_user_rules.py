def is_manager(user):
    return user.hierarchy.name == 'manager'

def is_salesman(user):
    return user.hierarchy.name == 'salesman'

def is_admin(user):
    return user.hierarchy.name == 'admin'