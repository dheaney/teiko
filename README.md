# Setup

## Setting up Python
With python3 or a virtual env, install all necessary libraries for this project:
```
python3 -m pip install -r requirements.txt
```

## Setting up the Database and Back-end
I chose PostgreSQL for my database. The application's access to the database can be configured through the `DATABASE_URL` environment variable, but the default is just `postgresql://username:password@localhost:5432/research_db`.

I used docker:
```
docker run -p 5432:5432 --name some-postgres -e POSTGRES_PASSWORD=postgres -d postgres
```

Once the database is running, configure with the `db.py` script:
```
python3 db.py
```

Then the CSV file from the problem statement can be imported with:
```
python3 load.py
```

When this is done, we are ready to run the back-end:
```
python3 app.py
```

## Setting up the Front-end

The front-end is a simple React app and can be started like this:
```
cd research-dashboard
npm install
npm start
```

# Database Schema

I split the data across 3 tables: Project, Subject, and Sample. Projects and Subjects are related to Samples by Foreign keys. For me this was the most natural way conceptually to separate the information in the CSV. This also allows us to scale more easily because we do not need to duplicate subject information as we add more samples.

# Design

The backend is a RESTful Flask application, so `app.py` primarily consists of endpoint definitions. The front-end is a React app that is primarily organized by components. The analytics described in the problem statement "run" automatically on the "Analytics Dashboard" page. This consists mainly in plotting boxplots with Plotly.js. When the responders q10 exceeds non-responders q90 (or vice versa), the analytics page marks the distributions as separable. With the given data, the CD4 T-Cell Distribution will be marked as separable.

Samples can be deleted from the Samples component, and new Samples can be added in in the Create Sample component. The extra filtering described in the problem statement can be performed with the "Filter" feature in the Samples component (The "Include Relations" switch needs to be turned "On" for this).