import json
import random
from sqlalchemy import Integer, text
from backend.jobs import add_jobs_to_db, delete_job_from_database
from backend.database_config import Session


class Employer:
    def __init__(self, name, logo_link, page_link, linkedin_page, industry, description, location, email, password,
                 contact_person_fullname, contact_person_phone_number, contact_person_email):
        self.id = Integer
        self.name = name
        self.logo_link = logo_link
        self.page_link = page_link
        self.linkedin_page = linkedin_page
        self.industry = industry
        self.description = description
        self.location = location
        self.email = email
        self.password = password
        self.contact_person_fullname = contact_person_fullname
        self.contact_person_phone_number = contact_person_phone_number
        self.contact_person_email = contact_person_email
        self.job_postings = []

    # Function to create the new user and add the info to the database
    def create_new_employer(self):
        session = Session
        try:
            session.execute(text('DROP TABLE employers_list'))
            session.commit()
            session.execute(text('''
                CREATE TABLE IF NOT EXISTS employers_list
                (id SERIAL PRIMARY KEY,
                 name TEXT,
                 logo_link TEXT,
                 page_link TEXT,
                 linkedin_page TEXT,
                 industry TEXT,
                 description TEXT,
                 location TEXT,
                 email TEXT,
                 password TEXT,
                 contact_person_fullname TEXT,
                 contact_person_phone_number TEXT,
                 contact_person_email TEXT,
                 job_postings JSON)
            '''))
            session.commit()

            if not check_if_employer_exists(self.email, self.location):  # Making sure the user doesn't exist already
                result = session.execute(text('''
                    INSERT INTO employers_list (name, logo_link, page_link, linkedin_page, industry, description, location,
                    email, password, contact_person_fullname, contact_person_phone_number, contact_person_email,
                    job_postings)
                    VALUES (:name, :logo_link, :page_link, :linkedin_page, :industry, :description, :location,
                    :email, :password, :contact_person_fullname, :contact_person_phone_number, :contact_person_email,
                    :job_postings)
                    RETURNING id
                '''), {
                    'name': self.name,
                    'logo_link': self.logo_link,
                    'page_link': self.page_link,
                    'linkedin_page': self.linkedin_page,
                    'industry': self.industry,
                    'description': self.description,
                    'location': self.location,
                    'email': self.email,
                    'password': self.password,
                    'contact_person_fullname': self.contact_person_fullname,
                    'contact_person_phone_number': self.contact_person_phone_number,
                    'contact_person_email': self.contact_person_email,
                    'job_postings': json.dumps(self.job_postings),
                })
                self.id = result.fetchone()[0]
                session.commit()

                # To view the table for testing
                results = session.execute(text('SELECT * FROM employers_list')).fetchall()
                session.commit()
                for result in results:
                    print(result)

                return f"Employer with name: {self.name} added successfully"
            else:
                return 'Email is already in use'
        except Exception as e:
            session.rollback()
            session.execute(text('''
                            CREATE TABLE IF NOT EXISTS employers_list
                            (id SERIAL PRIMARY KEY,
                             name TEXT,
                             logo_link TEXT,
                             page_link TEXT,
                             linkedin_page TEXT,
                             industry TEXT,
                             description TEXT,
                             location TEXT,
                             email TEXT,
                             password TEXT,
                             contact_person_fullname TEXT,
                             contact_person_phone_number TEXT,
                             contact_person_email TEXT,
                             job_postings JSON)
                        '''))
            session.commit()

            if not check_if_employer_exists(self.email, self.location):  # Making sure the user doesn't exist already
                result = session.execute(text('''
                                INSERT INTO employers_list (name, logo_link, page_link, linkedin_page, industry, description, location,
                                email, password, contact_person_fullname, contact_person_phone_number, contact_person_email,
                                job_postings)
                                VALUES (:name, :logo_link, :page_link, :linkedin_page, :industry, :description, :location,
                                :email, :password, :contact_person_fullname, :contact_person_phone_number, :contact_person_email,
                                :job_postings)
                                RETURNING id
                            '''), {
                    'name': self.name,
                    'logo_link': self.logo_link,
                    'page_link': self.page_link,
                    'linkedin_page': self.linkedin_page,
                    'industry': self.industry,
                    'description': self.description,
                    'location': self.location,
                    'email': self.email,
                    'password': self.password,
                    'contact_person_fullname': self.contact_person_fullname,
                    'contact_person_phone_number': self.contact_person_phone_number,
                    'contact_person_email': self.contact_person_email,
                    'job_postings': json.dumps(self.job_postings),
                })
                self.id = result.fetchone()[0]
                session.commit()

                # To view the table for testing
                results = session.execute(text('SELECT * FROM employers_list')).fetchall()
                session.commit()
                for result in results:
                    print(result)

                return f"Employer with name: {self.name} added successfully"
            else:
                return 'Company is already in use'
        finally:
            session.remove()

    def add_job_posting(self, title, city, state, remote, salary, date, url, description):
        session = Session
        id_exists = 'base'
        random_id = random.randint(100000000, 999999999)
        while id_exists is not None:
            random_id = random.randint(100000000, 999999999)
            try:
                id_exists = session.execute(text('''
                                    SELECT id FROM jobs 
                                    WHERE id = :id
                                '''), {
                    'id': random_id}).fetchone()
                session.commit()
            except Exception as e:
                session.rollback()
                id_exists = session.execute(text('''
                                                SELECT id FROM jobs 
                                                WHERE id = :id
                                            '''), {
                    'id': random_id}).fetchone()
                session.commit()

        try:
            job = {'id': random_id, 'title': title, 'company': self.name, 'company_logo': self.logo_link,
                   'location': city,
                   'state_code': state, 'latitude': None, 'longitude': None, 'remote': remote,
                   'avg_annual_salary_usd': None,
                   'salary': salary, 'date_posted': date, 'url': url, 'country_codes': [], 'cities': [],
                   'final_url': url,
                   'hiring_team': json.dumps([{'name': self.contact_person_fullname, 'email': self.contact_person_email}]),
                   'company_url': self.page_link, 'description': description, 'company_industry': self.industry,
                   'company_employee_count_range': None, 'company_linkedin_url': self.linkedin_page,
                   'company_description': self.description, 'company_city': self.location, 'company_postal_code': None,
                   'company_keywords': None}

            # Insert job into jobs table
            insert_query = text('''
                INSERT INTO jobs (id, title, company, company_logo, location, state_code, latitude, longitude, remote, 
                                  avg_annual_salary_usd, salary, date_posted, url, country_codes, cities, final_url, 
                                  hiring_team, company_url, description, company_industry, company_employee_count_range, 
                                  company_linkedin_url, company_description, company_city, company_postal_code, 
                                  company_keywords)
                VALUES (:id, :title, :company, :company_logo, :location, :state_code, :latitude, :longitude, :remote, 
                        :avg_annual_salary_usd, :salary, :date_posted, :url, :country_codes, :cities, :final_url, 
                        :hiring_team, :company_url, :description, :company_industry, :company_employee_count_range, 
                        :company_linkedin_url, :company_description, :company_city, :company_postal_code, 
                        :company_keywords)
            ''')

            session.execute(insert_query, job)
            session.commit()

            jobs = []
            jobs.append(job)
            add_jobs_to_db(jobs)
            job_postings = self.get_employee_parameter('job_postings')
            job_postings.append(job)
            self.update_employer_parameter('job_postings', json.dumps(job_postings))
            self.job_postings = self.get_employee_parameter('job_postings')
            return f"Successfully added job: {job}"
        except Exception as e:
            session.rollback()
            return f"Error adding job: {e}"

    def delete_job_posting(self, job_id):
        delete_job_from_database(job_id)
        job_postings = self.get_employee_parameter('job_postings')
        job_postings = [job for job in job_postings if job['id'] != job_id]
        self.update_employer_parameter('job_postings', json.dumps(job_postings))
        self.job_postings = self.get_employee_parameter('job_postings')

        return True

    def update_employer_parameter(self, parameter, new_value):
        # Ensure the parameter is a valid column name to prevent SQL injection
        valid_parameters = {'name', 'logo_link', 'page_link', 'linkedin_page', 'industry', 'description', 'location',
                            'email', 'password', 'contact_person_fullname', 'contact_person_phone_number',
                            'contact_person_email', 'job_postings'}
        if parameter not in valid_parameters:
            raise ValueError(f"Invalid parameter: {parameter}")

        this_session = Session
        try:
            this_session.execute(text(f'''
                            UPDATE employers_list
                            SET {parameter} = :new_value
                            WHERE name = :name AND email = :email AND password = :password
                        '''), {'new_value': new_value, 'name': self.name, 'email': self.email,
                               'password': self.password})

            this_session.commit()
        except Exception as e:
            this_session.rollback()
            this_session.execute(text(f'''
                                        UPDATE employers_list
                                        SET {parameter} = :new_value
                                        WHERE name = :name AND email = :email AND password = :password
                                    '''), {'new_value': new_value, 'name': self.name, 'email': self.email,
                                           'password': self.password})

            this_session.commit()
        finally:
            this_session.remove()

    def get_employee_parameter(self, parameter):
        # Ensure the parameter is a valid column name to prevent SQL injection
        valid_parameters = {'name', 'logo_link', 'page_link', 'linkedin_page', 'industry', 'description', 'location',
                            'email', 'password', 'contact_person_fullname', 'contact_person_phone_number',
                            'contact_person_email', 'job_postings'}
        if parameter not in valid_parameters:
            raise ValueError(f"Invalid parameter: {parameter}")

        this_session = Session

        try:
            result = this_session.execute(text(f'''
                            SELECT {parameter}
                            FROM employers_list
                            WHERE name = :name AND email = :email AND password = :password
                        '''), {'name': self.name, 'email': self.email,
                               'password': self.password}).fetchall()

            this_session.commit()
        except Exception as e:
            this_session.rollback()
            result = this_session.execute(text(f'''
                                        SELECT {parameter}
                                        FROM employers_list
                                        WHERE name = :name AND email = :email AND password = :password
                                    '''), {'name': self.name, 'email': self.email,
                                           'password': self.password}).fetchall()

            this_session.commit()
        finally:
            this_session.remove()

        if result:
            return result[0][0]
        else:
            return None


def check_if_employer_exists(name, location):
    session = Session
    try:
        result = session.execute(text('''
            SELECT EXISTS (
                SELECT 1 
                FROM employers_list 
                WHERE name = :name AND location = :location
            )
        '''), {'name': name, 'location': location}).scalar()
        session.commit()
    except Exception as e:
        session.rollback()
        result = session.execute(text('''
                    SELECT EXISTS (
                        SELECT 1 
                        FROM employers_list 
                        WHERE name = :name AND location = :location
                    )
                '''), {'name': name, 'location': location}).scalar()
        session.commit()
    finally:
        session.remove()
    return result


def employer_login(email, password):
    session = Session
    # To view the table for testing
    try:
        results = session.execute(text('SELECT * FROM employers_list')).fetchall()
        session.commit()
        for result in results:
            print(result)

        result = session.execute(text('''
                    SELECT id, name, logo_link, page_link, linkedin_page, industry, description, location, email, password,
                         contact_person_fullname, contact_person_phone_number, contact_person_email, job_postings
                    FROM employers_list
                    WHERE email = :email AND password = :password
                '''), {'email': email, 'password': password}).fetchone()
        session.commit()

        if result:
            employer = Employer(
                name=result[1],
                logo_link=result[2],
                page_link=result[3],
                linkedin_page=result[4],
                industry=result[5],
                description=result[6],
                location=result[7],
                email=result[8],
                password=result[9],
                contact_person_fullname=result[10],
                contact_person_phone_number=result[11],
                contact_person_email=result[12]
            )
            employer.id = result[0]
            employer.job_postings_ = result[13]
            return True, employer
        else:
            session.remove()
            return False, "Invalid credentials"
    except Exception as e:
        session.rollback()
        results = session.execute(text('SELECT * FROM employers_list')).fetchall()
        session.commit()
        for result in results:
            print(result)

        result = session.execute(text('''
            SELECT id, name, logo_link, page_link, linkedin_page, industry, description, location, email, password,
                 contact_person_fullname, contact_person_phone_number, contact_person_email, job_postings
            FROM employers_list
            WHERE email = :email AND password = :password
        '''), {'email': email, 'password': password}).fetchone()
        session.commit()

        if result:
            employer = Employer(
                name=result[1],
                logo_link=result[2],
                page_link=result[3],
                linkedin_page=result[4],
                industry=result[5],
                description=result[6],
                location=result[7],
                email=result[8],
                password=result[9],
                contact_person_fullname=result[10],
                contact_person_phone_number=result[11],
                contact_person_email=result[12]
            )
            employer.id = result[0]
            employer.job_postings_ = result[13]
            return True, employer
        else:
            session.remove()
            return False, "Invalid credentials"
    finally:
        session.remove()


def get_employer_from_email(email):
    session = Session
    try:
        result = session.execute(text('''
                    SELECT id, name, logo_link, page_link, linkedin_page, industry, description, location, email, password,
                         contact_person_fullname, contact_person_phone_number, contact_person_email, job_postings
                    FROM employers_list
                    WHERE email = :email
                '''), {'email': email}).fetchone()
        session.commit()
    except Exception as e:
        session.rollback()
        result = session.execute(text('''
                            SELECT id, name, logo_link, page_link, linkedin_page, industry, description, location, email, password,
                                 contact_person_fullname, contact_person_phone_number, contact_person_email, job_postings
                            FROM employers_list
                            WHERE email = :email
                        '''), {'email': email}).fetchone()
        session.commit()
    finally:
        session.remove()

    if result:
        employer = Employer(
            name=result[1],
            logo_link=result[2],
            page_link=result[3],
            linkedin_page=result[4],
            industry=result[5],
            description=result[6],
            location=result[7],
            email=result[8],
            password=result[9],
            contact_person_fullname=result[10],
            contact_person_phone_number=result[11],
            contact_person_email=result[12]
        )
        employer.id = result[0]
        employer.job_postings_ = result[13]
        return employer
    else:
        return 'No employer found for that email'
