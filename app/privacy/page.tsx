import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default function PrivacyPage() {
  return (
    <>
      <Header />
      <main className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="h1">Privacy Policy</h1>
        <p className="text-sm text-gray-500 mt-2">Last updated: July 12, 2026</p>
        <div className="prose mt-8 space-y-4 text-gray-700">

          <h2 className="h2 mt-8">1. What We Collect</h2>
          <p>
            ScheduleLink (operated by Otion LLC) collects only what we need to make scheduling work:
            your name and email from Google or Microsoft when you sign in, calendar tokens you grant
            us so we can read availability and write events, and the bookings made through your link.
          </p>
          <p>
            If you use our SMS features, we also collect your phone number, message content,
            delivery status, and timestamps for text messages sent or received through the Service.
          </p>
          <p>
            Payment information is processed securely through Stripe. We do not store credit card numbers.
          </p>

          <h2 className="h2 mt-8">2. How We Use Your Data</h2>
          <p>We use collected information to:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Provide, maintain, and improve the Service</li>
            <li>Schedule and confirm appointments</li>
            <li>Send SMS appointment reminders and confirmations</li>
            <li>Enable two-way communication between businesses and their customers</li>
            <li>Process deposits and payments via Stripe</li>
            <li>Synchronize with Google Calendar and Microsoft Outlook</li>
            <li>Provide customer support</li>
          </ul>

          <h2 className="h2 mt-8">3. SMS & Text Messaging</h2>
          <p>
            ScheduleLink uses SMS to send appointment confirmations, reminders, and
            facilitate communication between service providers and their clients.
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Message frequency</strong> — varies based on your activity. You typically receive 2–6 messages per booking (confirmation, reminders, and optional two-way communication).</li>
            <li><strong>Opt-out</strong> — Reply <strong>STOP</strong>, <strong>CANCEL</strong>, <strong>END</strong>, or <strong>UNSUBSCRIBE</strong> at any time to stop receiving SMS messages. You will receive one final confirmation message.</li>
            <li><strong>Help</strong> — Reply <strong>HELP</strong> for assistance with the Service.</li>
            <li><strong>Cost</strong> — Message and data rates may apply. Contact your mobile carrier for pricing.</li>
            <li><strong>Marketing</strong> — We do not send marketing or promotional SMS without your separate consent.</li>
          </ul>
          <p className="font-semibold">
            Mobile information and messaging consent will not be shared with third parties
            or affiliates for marketing or promotional purposes.
          </p>
          <p>
            By providing your phone number and consenting to receive SMS messages, you agree to
            receive automated booking confirmations, reminders, and service-related messages.
            Consent is not a condition of purchase. Text STOP to cancel or HELP for help.
            Message frequency varies. Message and data rates may apply.
          </p>

          <h2 className="h2 mt-8">4. Data Sharing</h2>
          <p>
            We never sell your personal information. We never share attendee email or phone
            with third parties. Tokens are encrypted at rest.
          </p>
          <p>We share data only with service providers necessary to operate the Service:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Twilio</strong> — SMS delivery and phone number management</li>
            <li><strong>Stripe</strong> — Payment processing</li>
            <li><strong>Google</strong> — Calendar API</li>
            <li><strong>Microsoft</strong> — Calendar API (Graph)</li>
            <li><strong>Vercel</strong> — Web hosting</li>
            <li><strong>Zoho</strong> — Email notifications</li>
          </ul>

          <h2 className="h2 mt-8">5. Data Retention</h2>
          <p>
            We retain your information for as long as your account is active or as
            needed to provide the Service. SMS message content and metadata are
            retained for up to 12 months. You may request deletion of your data at
            any time.
          </p>

          <h2 className="h2 mt-8">6. Your Rights</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>Access, update, or delete your personal information</li>
            <li>Opt out of SMS at any time by replying STOP</li>
            <li>Revoke OAuth access to your calendar</li>
            <li>Request a copy of your data</li>
          </ul>

          <h2 className="h2 mt-8">7. Google API Limited Use Disclosure</h2>
          <p>
            ScheduleLink's use and transfer of information received from Google APIs
            will adhere to the{" "}
            <a className="text-primary-600" href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer">
              Google API Services User Data Policy
            </a>
            , including the Limited Use requirements. ScheduleLink only uses Google
            user data (name, email, calendar tokens, and calendar events) to provide,
            maintain, and improve the scheduling service. Google user data is not
            used for advertising, AI training, data sales, or any purpose beyond
            delivering core app functionality. Data is not shared with third parties
            except as necessary to provide the Service and in compliance with
            Google's Limited Use requirements.
          </p>

          <h2 className="h2 mt-8">8. Contact</h2>
          <p>
            For questions or to exercise your data rights:
          </p>
          <p>
            Email: <a className="text-primary-600" href="mailto:support@schedulelink.tech">support@schedulelink.tech</a>
          </p>

        </div>
      </main>
      <Footer />
    </>
  );
}
