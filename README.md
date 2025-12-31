# Rezify: AI Powered Internship Searching Site Designed for Students

This Python project combines resume reading technology and job searching. It utilizes the Azure OpenAI API for resume reading and internship suggesting, and Adzuna, Careerjet, and Jooble API's for internship searching.

## Rezify

### First Step - Suggesting Internships Based on Resume

- Through the flask application, a resume needs to be uploaded through the main center button.
- When 'Search Internships' is selected, the code begins to use AI to read the resume.
- Location can be specified as well.
- The script connects to the Azure OpenAI API, asking it to give internships that the person should be looking for based on their resume.
- 5-7 Internship titles are returned.

### Second Step - Finding Internships Listings

- After the internship titles are given, the script simultaneously connects to the Adzuna, CareerJet, and Jooble API's.
- The script searches for live internships for each of the internship recommendations given.
- The code accumulates jobs found from all 3 API's.
- The jobs run through an algorithm, filtering out poor results and removing duplicates.

### Third Step - Filtering Results

- The results page allows users to filter the results given.
- The application allows you to select which internship titles you want to see the results for.
- So, if the application suggests an interships that you don't think fits you, you can filter out results easily.
- You can also sort the results by the date they were posted.

### Usage

To use Rezify:

1. Ensure you have the necessary credentials for the Azure OpenAI, Adzuna, CareerJet, and Jooble APIs.
2. Install the required Python libraries listed in the `requirements.txt` file.
3. Run the script.
4. Follow the output to the application.
5. Upload your resume, and select the location if preffered.
6. Results of live intership listings based on your resume will be shown.

### Stripe

To test Stripe:

1. Install Stripe Client (for handling webhooks): https://docs.stripe.com/stripe-cli
2. Run in another terminal: stripe listen --forward-to 127.0.0.1:5000/api/stripe_webhook
3. Copy and paste the webhook secret into the top of payment.py for the variable endpoint_secret
4. Upgrade to Premium plan in a non rezify/school-partnered account and use credit card number (4242 4242 4242 4242), put anything for other credit card information
