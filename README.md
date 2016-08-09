# VoteBot-Forms

## Motivation
Online voter registration should be easy. Unfortunately, each state has their own form design. This application provides a nice API that abstracts across them, and falls back to the National Voter Registration Form when online registration is not possible.

## Usage
POST to '/registration' with json like
```
{ 
  callback_url: '/callback',
  user: {
    "first_name":"John",
    "middle_name":"Q",
    "last_name":"Public",
    "date_of_birth":"1950-12-25",
    "address":"314 Test St",
    "city":"Schenectady",
    "state":"NY",
    "zip":"12345",
    "phone":"123-456-7890",
    "email":"text@example.com"
    "state_id_number":"NONE",
    "political_party":"No Party",
    "us_citizen":true,
    "legal_resident": true,
    "disenfranchised":false,
  }
}
```

receive a response like
```
{
    "status": "queued"
}
```

get a POST to your callback_url like
```
{
    "pdf_url": "https://ldv-bullwinkle-production.s3.amazonaws.com/voter_registration_forms/user_XXXXXX_YYYYMMDDHHMMSS_HASH.pdf?access_token" // for print and mail
}
```
or 
```
{
    "status": "success" // for state OVR
    "missing_fields": [],
}
```

## Development
- `virtualenv .venv; source .venv/bin/activate`
- `pip install -r requirements/development.txt`
- `python manager.py runserver`
- in another terminal `python manager.py rq worker`

## Testing
- fill `tests/secrets.yml` with valid identification information. ensure dates are iso-formatted strings
- eg `
    NY: 
      first_name: John
      middle_name: Q
      last_name: Public
      date_of_birth: "1950-12-25"
      address: 314 Test St
      city: Schenectady
      state: NY
      zip: 12345
      phone: 123-456-7890
      email: text@example.com
      state_id_number: NONE
      political_party: No Party
      us_citizen:true
      legal_resident:true
      disenfranchised:false
`
- run `python tests/run.py`

## Security
- Requires PyOpenSSL and ndg-httpsclient for improved SSL certificate validation. California's system won't validate without it...

## Deployment
- run on Heroku under uwsgi w/ gevent
- TBD
