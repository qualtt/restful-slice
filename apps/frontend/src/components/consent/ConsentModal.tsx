interface ConsentModalProps {
  open: boolean;
  onAccept: () => void;
}

export function ConsentModal({ open, onAccept }: ConsentModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'url(https://www.transparenttextures.com/patterns/diagmonds-light.png)' }}>
      <div className="w-full max-w-lg window-2002 shadow-[2px_2px_0px_#000]">
        <div className="window-title-2002 flex justify-between">
          <span>Data Processing Consent</span>
          <button className="bg-[#c0c0c0] text-black border border-t-white border-l-white border-b-gray-800 border-r-gray-800 px-1 font-bold leading-none">X</button>
        </div>
        <div className="p-4">
          <div className="flex gap-4">
            <div>
              <p className="text-sm text-black">
                We collect product analytics, diagnostics, and profile information to improve
                slicing quality, reliability, and support. By accepting, you consent to this
                processing under Terms of Service and Privacy Policy.
              </p>
              <div className="mt-4 border-2 border-t-gray-800 border-l-gray-800 border-b-white border-r-white bg-white p-2 h-24 overflow-y-scroll text-xs text-black">
                <ul className="list-disc pl-4">
                  <li>Device and browser context</li>
                  <li>Page usage and clickstream events</li>
                  <li>Client-side errors for diagnostics</li>
                </ul>
              </div>
            </div>
          </div>
          <div className="mt-6 flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={onAccept}
              className="btn-2002 w-24"
            >
              OK
            </button>
            <button type="button" className="btn-2002 w-24" disabled>
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
