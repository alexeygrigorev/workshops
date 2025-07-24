# Create a Coding Agent

## Generate the template django project

Let's start a new Django project

```bash
mkdir django_template
cd django_template/

uv init
rm main.py

uv add django

uv run django-admin startproject myproject .
uv run python manage.py startapp myapp
```

Add the new app (`myapp`) into `myproject/settings.py`'s `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... other apps
    'myapp',
]
```

For our convenience, we can have a `Makefile` with useful commands:

```makefile
.PHONY: install migrate run

install:
	uv sync --dev

migrate:
	uv run python manage.py migrate

run:
	uv run python manage.py runserver
```

Next, create the base html template in `templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{% endblock %}</title>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

Add this templates directory to the settings file:

```python
TEMPLATES = [{
    'DIRS': [BASE_DIR / 'templates'],
    ...
}
```

Now we're ready to create the home view for our app:

```python
# myapp/views.py
def home(request):
    return render(request, 'home.html')

# myproject/urls.py
from myapp import views

urlpatterns = [
    # ...
    path('', views.home, name='home'),
]
```

HTML code for `myapp/templates/home.html`:

```html
{% extends 'base.html' %}

{% block content %}
<h1>Home</h1>
{% endblock %}
```



Finally, let's add TailwindCSS and Font-Awesome to our `base.html` template:

```html
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css" rel="stylesheet">
```

We can update `base.html` with [this code](django_template/templates/base.html).
