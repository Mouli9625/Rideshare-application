@echo off
mkdir rideshare_app
cd rideshare_app

mkdir static templates models routes utils

mkdir static\css static\images
mkdir templates\auth templates\rider templates\driver templates\manager

copy NUL static\css\main.css
copy NUL static\css\dashboard.css
copy NUL static\css\forms.css

copy NUL templates\base.html
copy NUL templates\auth\login.html
copy NUL templates\auth\register.html
copy NUL templates\rider\dashboard.html
copy NUL templates\rider\book_ride.html
copy NUL templates\rider\ride_history.html
copy NUL templates\driver\dashboard.html
copy NUL templates\driver\active_rides.html
copy NUL templates\driver\area_rides.html
copy NUL templates\manager\dashboard.html
copy NUL templates\manager\cost_analysis.html
copy NUL templates\manager\reports.html

copy NUL models\__init__.py
copy NUL models\user.py
copy NUL models\ride.py
copy NUL models\area.py

copy NUL routes\__init__.py
copy NUL routes\auth.py
copy NUL routes\rider.py
copy NUL routes\driver.py
copy NUL routes\manager.py

copy NUL utils\__init__.py
copy NUL utils\db.py
copy NUL utils\auth.py
copy NUL utils\decorators.py

copy NUL config.py
copy NUL requirements.txt
copy NUL app.py
copy NUL README.md
@echo Directory structure created successfully!
