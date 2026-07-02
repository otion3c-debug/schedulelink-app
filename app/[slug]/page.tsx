import Header from "@/components/Header";
import Footer from "@/components/Footer";
import BookingWidget from "@/components/BookingWidget";

export const dynamic = "force-dynamic";

export default function PublicBookingPage({ params }: { params: { slug: string } }) {
  return (
    <>
      <Header />
      <main className="max-w-3xl mx-auto px-6 py-12">
        <div className="card p-6">
          <BookingWidget slug={params.slug} />
        </div>
      </main>
      <Footer />
    </>
  );
}
