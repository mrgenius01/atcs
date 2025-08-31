from django.test import Client

def test_home_requires_login():
    c = Client()
    resp = c.get("/")
    assert resp.status_code == 302  # redirect to login
