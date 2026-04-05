import Link from 'next/link';

export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen bg-[#f4f8fe] px-4 py-10">
      <div className="container-paytm max-w-2xl">
        <div className="paytm-surface p-8 text-center sm:p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#0a58d8]">Access Control</p>
          <h1 className="mt-3 text-3xl font-black text-[#062a64]">Unauthorized</h1>
          <p className="mt-3 text-sm text-slate-600">
            Your account does not have permission to view this route. Sign in with the correct role and try again.
          </p>

          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link href="/login" className="rounded-xl bg-[#002970] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#0a3f9d]">
              Go to Login
            </Link>
            <Link href="/" className="rounded-xl border border-[#bfd3f2] px-5 py-2.5 text-sm font-bold text-[#0a58d8] hover:bg-[#edf5ff]">
              Back Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
