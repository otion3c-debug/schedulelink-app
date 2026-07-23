import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import PricingCards from "@/components/PricingCards";

/* ---- SVG Icons ---- */

function IconCalendar() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4" /><path d="M8 2v4" /><path d="M3 10h18" />
      <path d="M8 14h.01" /><path d="M12 14h.01" /><path d="M16 14h.01" />
      <path d="M8 18h.01" /><path d="M12 18h.01" /><path d="M16 18h.01" />
    </svg>
  );
}

function IconCode() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  );
}

function IconZap() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10" />
    </svg>
  );
}

function IconMail() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="M22 4L12 13 2 4" />
    </svg>
  );
}

function IconShield() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

export default function HomePage() {
  return (
    <>
      <Header />
      <main>

        {/* HERO */}
        <section className="relative max-w-6xl mx-auto px-6 pt-20 pb-12 text-center overflow-hidden">
          {/* Subtle background glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-gradient-to-b from-primary-500/5 to-transparent rounded-full pointer-events-none" />
          <h1 className="h1 text-balance relative">
            Stop playing <span className="text-primary-500">phone tag</span>.<br />
            Book clients in 3 clicks.
          </h1>
          <p className="mt-5 text-lg text-gray-600 max-w-2xl mx-auto text-balance">
            Connect Google or Microsoft Calendar, share your booking link, and let clients
            pick a time that works — automatically. No back-and-forth emails. No double-bookings.
          </p>
          <div className="mt-7 flex items-center justify-center gap-3">
            <Link href="/login" className="btn-primary px-6 py-3 text-base shadow-lg shadow-primary-500/20">Get started — free</Link>
            <Link href="/pricing" className="btn-secondary px-6 py-3 text-base">See pricing</Link>
          </div>
          <p className="mt-2 text-sm text-gray-400">5 free bookings per month. No credit card required.</p>

          {/* Trust bar */}
          <div className="mt-8 flex items-center justify-center gap-6 text-sm text-gray-400">
            <span className="flex items-center gap-1.5">
              <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5 text-secondary-500"><path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg>
              Google sign-in
            </span>
            <span className="flex items-center gap-1.5">
              <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5 text-secondary-500"><path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg>
              Stripe payments
            </span>
            <span className="flex items-center gap-1.5">
              <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5 text-secondary-500"><path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg>
              Free to start
            </span>
          </div>
        </section>

        {/* PROMO VIDEO */}
        <section className="max-w-xs mx-auto px-6 pb-16">
          <div className="rounded-2xl overflow-hidden shadow-lg border border-gray-200 bg-black">
            <video
              src="/promo.mp4"
              controls
              playsInline
              poster="/promo-poster.jpg"
              className="w-full h-auto"
            >
              Your browser doesn't support video. <a href="/promo.mp4" className="text-primary-500">Download it</a>.
            </video>
          </div>
          <p className="text-center text-sm text-gray-500 mt-3">
            25-second overview — ScheduleLink in action
          </p>
        </section>

        {/* HOW IT WORKS */}
        <section className="bg-gray-50 border-t border-b border-gray-200 py-16">
          <div className="max-w-6xl mx-auto px-6">
            <h2 className="h2 text-center">How it works</h2>
            <div className="mt-12 grid md:grid-cols-3 gap-8">
              {[
                { step: "1", title: "Sign in with Google or Microsoft", desc: "Connect your calendar in one click. We sync your real availability so you're never double-booked." },
                { step: "2", title: "Share your link", desc: "Send your personalized booking page. Or upgrade to Pro+ and embed a widget directly on your site." },
                { step: "3", title: "Get booked", desc: "Clients pick a time. Both calendars update instantly. Confirmation goes out automatically." },
              ].map((s) => (
                <div key={s.step} className="text-center">
                  <div className="w-12 h-12 rounded-full bg-primary-500 text-white text-lg font-bold flex items-center justify-center mx-auto shadow-md shadow-primary-500/20">
                    {s.step}
                  </div>
                  <h3 className="mt-4 font-semibold text-lg text-gray-900">{s.title}</h3>
                  <p className="mt-2 text-sm text-gray-600 max-w-xs mx-auto">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section id="features" className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="h2 text-center">Everything you need</h2>
          <div className="mt-12 grid md:grid-cols-3 gap-6">
            {[
              {
                icon: <IconCalendar />,
                title: "Multi-calendar sync",
                body: "Connect Google Calendar and Microsoft Outlook. We check your real availability and write events back automatically.",
              },
              {
                icon: <IconCode />,
                title: "Embeddable widget",
                body: "Drop a single script tag on your site and your booking widget appears. Customize colors, header, and footer.",
                badge: "Pro+",
              },
              {
                icon: <IconZap />,
                title: "Quick and simple setup",
                body: "Sign in with Google or Microsoft, set your hours in about 2 minutes, share your link. No configuration sprawl.",
              },
              {
                icon: <IconMail />,
                title: "Automated confirmations",
                body: "Clients receive email confirmations the moment they book. No manual follow-ups needed.",
              },
              {
                icon: <IconShield />,
                title: "Privacy first",
                body: "Your data stays between you and your calendar. Google sign-in, Stripe payments, no third-party access.",
              },
            ].map((f: any) => (
              <div key={f.title} className="card p-6 hover:shadow-lg hover:border-primary-100 transition-all duration-200 group">
                <div className="w-10 h-10 rounded-lg bg-primary-50 text-primary-500 flex items-center justify-center group-hover:bg-primary-100 transition-colors">
                  {f.icon}
                </div>
                <h3 className="mt-4 font-semibold text-lg text-gray-900">
                  {f.title}
                  {f.badge && (
                    <span className="ml-2 text-xs font-semibold text-secondary-700 bg-secondary-50 px-2 py-0.5 rounded-full align-middle">
                      {f.badge}
                    </span>
                  )}
                </h3>
                <p className="mt-2 text-sm text-gray-600 leading-relaxed">{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* TESTIMONIALS */}
        <section className="max-w-4xl mx-auto px-6 py-16">
          <h2 className="h2 text-center">Trusted by professionals</h2>
          <p className="mt-2 text-center text-gray-500">ScheduleLink is just getting started — but the people using it already love it.</p>
          <div className="mt-10 grid md:grid-cols-3 gap-6">
            {/* Testimonial 1 — Victoria */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 text-center hover:border-primary-200 transition-colors">
              <div className="text-4xl mb-3 text-primary-500 font-serif leading-none">"</div>
              <p className="text-sm text-gray-700 italic leading-relaxed">
                It was easy to open and use, the directions were very clear and I didn't have to wonder what to do next. I will use it and recommend it as well.
              </p>
              <div className="mt-4 flex items-center justify-center gap-2">
                <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center text-xs font-bold">V</div>
                <div>
                  <div className="text-sm font-medium text-gray-900">Victoria</div>
                  <div className="text-xs text-gray-400">Educator, Poughkeepsie NY</div>
                </div>
              </div>
            </div>
            {/* Testimonial 2 — Kareem */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 text-center hover:border-primary-200 transition-colors">
              <div className="text-4xl mb-3 text-primary-500 font-serif leading-none">"</div>
              <p className="text-sm text-gray-700 italic leading-relaxed">
                Very impressed with ScheduleLink. The platform is clean, simple and makes scheduling meetings incredibly easy. Love how fast and professional the experience feels. Definitely a great tool for anyone wanting to save time and avoid back and forth emails.
              </p>
              <div className="mt-4 flex items-center justify-center gap-2">
                <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center text-xs font-bold">K</div>
                <div>
                  <div className="text-sm font-medium text-gray-900">Kareem P.</div>
                  <div className="text-xs text-gray-400">Entrepreneur, Buford GA</div>
                </div>
              </div>
            </div>
            {/* Testimonial 3 — Marcus */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 text-center hover:border-primary-200 transition-colors">
              <div className="text-4xl mb-3 text-primary-500 font-serif leading-none">"</div>
              <p className="text-sm text-gray-700 italic leading-relaxed">
                As a business coach, my calendar is my business. ScheduleLink cut my booking admin in half. Clients love how easy it is to grab a time — and I love not having to chase them down.
              </p>
              <div className="mt-4 flex items-center justify-center gap-2">
                <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center text-xs font-bold">M</div>
                <div>
                  <div className="text-sm font-medium text-gray-900">Marcus R.</div>
                  <div className="text-xs text-gray-400">Business Coach, Austin TX</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* PRICING */}
        <section id="pricing" className="bg-gray-50 border-t border-b border-gray-200 py-16">
          <div className="max-w-6xl mx-auto px-6">
            <h2 className="h2 text-center">Simple pricing.</h2>
            <p className="mt-2 text-center text-gray-600">Start free. Upgrade when you outgrow it.</p>
            <div className="mt-10">
              <PricingCards />
            </div>
          </div>
        </section>

        {/* BOTTOM CTA */}
        <section className="relative max-w-3xl mx-auto px-6 py-20 text-center overflow-hidden">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[200px] bg-gradient-to-b from-secondary-500/5 to-transparent rounded-full pointer-events-none" />
          <h2 className="h2 relative">Ready to stop the back-and-forth?</h2>
          <p className="mt-4 text-lg text-gray-600">Setting up your booking page is quick, simple and free to start.</p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link href="/login" className="btn-primary px-8 py-3 text-lg shadow-lg shadow-primary-500/20">Get started — free</Link>
            <Link href="/pricing" className="btn-secondary px-8 py-3 text-lg">See pricing</Link>
          </div>
          <p className="mt-3 text-sm text-gray-400">No credit card needed. Powered by Google & Stripe.</p>
        </section>

      </main>
      <Footer />
    </>
  );
}
