import { useNavigate } from "react-router-dom";
import "driver.js/dist/driver.css";
import "../styles/TutorialDriver.css";
import '../styles/NewIndexPage.css';

function IndexFeatures({ theme, transitionOverlayRef }) {
    const navigate = useNavigate(); //SPA (Single-page-architecture) navigator
    const isRootDomain = window.location.hostname.split(".").length === 2;

  return (
    <>
      <h2 id="features-section" className="section-title">Features & Filters</h2>
      <section className="features">
        <div className="feature text-left-image-right">
          <h2>Instant AI-Powered Matching</h2>
          <div className="feature-split">
            <div className="feature-text">
              <p>
                Just upload your resume. Our AI instantly parses and analyzes your skills. No need to manually fill out your skills and experiences.
                You will be looking at matched opportunities in <strong>under 30 seconds.</strong>
              </p>
            </div>
            <div className="feature-image">
              <img style={{ width: '80%' }} src="/static/results.png" alt="AI Matching Illustration" />
            </div>
          </div>
        </div>
        <div className="feature text-left-image-right">
          <h2>All Opportunities Seen</h2>
          <div className="feature-split">
            <div className="feature-text">
              <p>
                With Rezify, users can be confident that they aren't missing any opportunities. Our database updates every
                hour with postings from over <strong>20 of the largest job boards</strong>, as well as directly
                from company posting pages.
              </p>
            </div>
            <div className="feature-image">
              <img src="/static/data-filter-icon-vector.jpg" alt="Job Accumulation Gathering" />
            </div>
          </div>
        </div>
        <div className="feature">
          <h2>Broad & Customizable Search</h2>
          <p>
            Our AI will initially generate 4 search terms based on your skills, allowing you to search for
            <strong> positions that you may not have known you were qualified for</strong>.
          </p>
          <img src="/static/search_filters.png" alt="Search Terms Example" />
          <p>
            Selecting a search term will <strong>isolate</strong> your results for based on that term. You can customize your search by <strong>adding </strong>
            or <strong>removing</strong> search terms.
          </p>
        </div>
        <div className="feature">
          <h2>Filters</h2>
          <img src="/static/filters_box.png" alt="Filters Box" />
          <p>
            Filter for <strong>in-person/remote</strong> positions, by <strong>location</strong>, by <strong>industry</strong>,
            or whether or not the position is open for <strong>international students</strong>.
          </p>
        </div>
        <div className="feature">
          <h2>Be The First To Apply</h2>
          <img src="/static/recently_posted.png" alt="Recently Posted" />
          <p>
            <strong>Sort by date</strong> and see the most recently posted opportunities first. Our database <strong>updates hourly</strong> with the newest
            postings from across the internet.
          </p>
        </div>
        <div className="feature">
          <h2>Keep Track Of Your Applications</h2>
          <img src="/static/applied_to.png" alt="Recently Posted" />
          <p>
            Mark jobs applied to so you can keep track of <strong>your applications</strong> and keep job descriptions. When you mark a job as 'Applied To',
            it will be <strong>removed from your results</strong>, so you can focus on <strong>new opportunities</strong>. You can view your positions applied to on the
            <strong> 'Applied To' </strong> tab.
          </p>
        </div>
        <div className="feature">
          <h2>LinkedIn Connection Outreach</h2>
          <img src="/static/linkedin_messaging.png" alt="Recently Posted" />
          <p>
            Easily find people to <strong>connect with on LinkedIn</strong> at companies you are interested in.
            You can find <strong>alumni</strong> from your school or <strong>recruiters</strong>.
            Reach out and make connections to increase your chances of landing an interview.
            We provide a <strong>personalized message template</strong> using your resume and the job description to help you get started.
          </p>
        </div>
        <div className="feature text-left-image-right">
          <h2>Other Key Features</h2>
          <div className="feature-split">
            <div className="feature-text">
              <ul>
                <li>Self-cleaning database, <strong>removing expired postings</strong> daily.</li>
                <li>Mark postings as 'Favorites' and view them in the 'Favorites' tab.</li>
                <li><strong>Remove any job</strong> from your results for any reason.</li>
                <li>Change resumes and get <strong>new calibrated results</strong>.</li>
              </ul>
            </div>
            <div className="feature-image">
              <img style={{ width: '80%', boxShadow: 'none' }} src="/static/rezify_logo2.png" alt="AI Matching Illustration" />
            </div>
          </div>
        </div>
        <div className="feature text-left-image-right">
          <h2>New Features Soon</h2>
          <div className="feature-split">
            <div className="feature-text">
                <p>
                    Rezify is <strong>constantly evolving</strong>, adding new features rapidly. We are made <strong>by students for students</strong>, adhering
                    to the wants and needs of our peers. We are eager to hear from our community, please use our <strong>feedback form</strong> to let us know what you want to see next,
                     or just to share your opinion.
                </p>
            </div>
            <div className="feature-image">
              <a href="/feedback"
               target="_blank"
               class="hero-nav__btn">Feedback</a>
            </div>
          </div>
        </div>
      </section>

      {isRootDomain && (
          <>

          <h2 className="section-title">Pricing Plans</h2>
          <section id="pricing-plans" className="plans-section">
              <div className="plans-flex-container">
                {/* Left side - Feature card */}
                <div className="plans-feature-card feature">
                  <h2>Pricing Info</h2>
                  <div className="feature-text">
                  <ul>
                    <li>All transactions & billing securely handled by <strong>Stripe</strong>.</li>
                    <li><strong>Cancel easily</strong> at any time, for any reason.</li>
                    <li>With <strong>premium</strong>, unlock <strong>unlimited access</strong> to all of our features!</li>
                 </ul>
                 <a href="#features-section" style={{ "text-decoration": "none"}}>See a breakdown of our features here</a>
                 <p>Good news! If your <strong>Univeristy partners with Rezify</strong>, you get premium access for <strong>Free!</strong></p>
                 </div>
                </div>

                {/* Right side - Pricing plans */}
                <div className="plans-container">
                        <div className="plan-card" style={{border: '4px solid #333'}}>
                            <div className="plan-left">
                                <h2>Free Plan</h2>
                                <h3>$0.00/month</h3>
                            </div>
                            <ul>
                                <li>4 Search Titles</li>
                                <li>Results Refresh Weekly</li>
                                <li>25 Results Per Search</li>
                                <li>Max 1 Resume</li>
                            </ul>
                        </div>

                        <div className="plan-card" style={{backgroundColor: "color-mix(in srgb, white, var(--primary-color) 20%)", border: "4px solid var(--primary-aw)"}}>
                            <div className="plan-left">
                                <h2 style={{"color": 'color-mix(in srgb, var(--primary-color), black 20%)'}}>Premium Plan</h2>
                                <h3 style={{"color": 'color-mix(in srgb, var(--primary-color), black 20%)'}}>$4.99/month</h3>
                            </div>
                            <ul>
                                <li style={{"color": 'color-mix(in srgb, var(--primary-color), black 20%)'}}><div className="emoji">🔧</div><b>Fully Customizable Search</b></li>
                                <li style={{"color": 'color-mix(in srgb, var(--primary-color), black 20%)'}}><div className="emoji">⏱️</div><b>24/7 Up-To-Date Results</b></li>
                                <li style={{"color": 'color-mix(in srgb, var(--primary-color), black 20%)'}}><div className="emoji">🔎</div><b>Unlimited Results</b></li>
                                <li style={{"color": 'color-mix(in srgb, var(--primary-color), black 20%)'}}><div className="emoji">📄</div><b>Unlimited Resumes</b></li>
                            </ul>

                    </div>
                </div>
              </div>
            </section>

          <section id="university-info-section" className="university-info-section">
            <h2 style={{ "margin-top": "70px" }} className="section-title">For Colleges & Universities</h2>

            <div className="university-feature-card">
                {/* Left column - text */}
                <div className="university-col-left">
                  <h2>Benefits</h2>
                  <div className="feature-text">
                  <ul>
                    <li><strong>Premium</strong> level access for entire student base.</li>
                    <li>Custom school themed portal & secure domain.</li>
                    <li>H1 filter for <strong>international students.</strong></li>
                    <li>Career center employees can view student usage statistics in our <strong>admin dashboard</strong>, including:
                        <ul>
                        <li>Student usage over time</li>
                        <li>Jobs applied to (total & per student)</li>
                        <li>Number of job matches per student</li>
                        <li><strong>Jobs accepted by students</strong></li>
                        <li>Search trends & analytics</li>
                        <li>Favorite jobs, jobs applied to, and usage for individual students</li>
                        </ul>
                  </li>
                 </ul>
                 </div>
                </div>

                {/* Middle column - stacked images */}
                <div className="university-col-center">
                  <img src="/static/college_portal.png" alt="Custom Portal" />
                  <img src="/static/admin_dash.png" alt="Admin Dashboard" />
                </div>

                {/* Right column - text */}
                <div className="university-col-right">
                  <div className="feature-text">
                  <ul>
                    <li>Industry standard data security.</li>
                    <li>Easy set up & integration - <strong>within 1 day!</strong></li>
                    <li>Integrate university SSO upon request.</li>
                    <li>Pricing plans starting at $1,000 for a 6-month trial.</li>
                    <li>Have a select group of students (5-20) try premium before-hand for cheap!</li>
                 </ul>
                 <button class="demo-request-button" onClick={() => navigate('/get_demo')}>
                    Contact Sales / Request Demo
                </button>
                 </div>
                </div>
              </div>

          </section>

          {/* Map - Hide for now until we have more schools
          <section id="rezify-map-showcase" className="map-showcase-section">
            <div className="container">
              <h2 className="section-title">Rezify's Growing Impact</h2>
              <p className="section-lead">
                Students and universities across the nation are leveraging Rezify to transform career readiness.
                See some of the institutions where Rezify is making a difference.
              </p>
              <div className="map-container">
                <div
                  className="map-marker"
                  style={{ top: '55.5%', left: '65%' }}
                  data-tooltip="Missouri S&T - Rolla, MO"
                >
                  <div className="marker-flag-pin">
                    <div className="flag-shape"></div>
                    <div className="flag-pole"></div>
                  </div>
                  <span className="marker-label">Missouri S&T</span>
                </div>
              </div>
            </div>
          </section>
            */}

    </>
    )}

      <section id="about-us-section" className="about-us-section">
          <h2 className="section-title" style={{ marginBottom: "40px" }}>About Us</h2>

          <div className="about-us-flex">
            {/* Left: About paragraph card */}
              <div className="feature about-card">
                <div className="about-us-text">
                <h2>Who We Are</h2>
                <p>
                  Rezify was founded by 2 college students from St. Louis, MO in early 2024. After a frustrating year of internship searching with little luck,
                  <strong> Ishan Dhawan (Computer Science & AI, Georgia Tech)</strong> and <strong>Peter Hogan (Data Science, Purdue)</strong> decided to create a solution that would help students like themselves.
                  Since then, Rezify has been evolving and innovating with new features and improvements, all while keeping the student experience at the forefront.
                  Since we are students ourselves, we understand the challenges and needs of our peers, and we are committed to making the internship search process as efficient and effective as possible.

                </p>
              </div>
            </div>

            {/* Right: YouTube embed */}
            <div className="about-us-video">
              <div className="video-wrapper">
                <iframe
                  width="100%"
                  height="315"
                  src="https://www.youtube.com/embed/zgzaiHOiOmc?si=YtDefqoXlKdt22Dt"
                  title="Rezify Demo Video"
                  frameBorder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                ></iframe>
              </div>
            </div>
          </div>
        </section>


      <div id="loading-overlay">
        Finding internships, please wait...
      </div>
      <div className="transition-overlay" ref={transitionOverlayRef}>
        <img src={theme.logo} alt="Logo" />
        <p>Loading Internships...</p>
        <div className="spinner" />
      </div>
    </>
  );
}

export { IndexFeatures };
