import Header from "@/components/Header";
import Footer from "@/components/Footer";
import PricingCards from "@/components/PricingCards";

export default function PricingPage() {
  return (
    <>
      <Header />
      <main className="max-w-6xl mx-auto px-6 py-16">
        <h1 className="h1 text-center">Pricing</h1>
        <p className="mt-3 text-center text-gray-600">
          Pick the plan that fits. Cancel anytime.
        </p>
        <div className="mt-10">
          <PricingCards />
        </div>
      </main>
      <Footer />
    </>
  );
}
