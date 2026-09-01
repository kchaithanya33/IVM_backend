function AzureLogo() {
  return (
    <svg
      className="azure-logo"
      viewBox="0 0 64 64"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Azure"
    >
      <path
        d="M35.5 5L17 51h12.2l5.1-13.3h17.1L42.6 20.5 35.5 5z"
        fill="#0078D4"
      />

      <path
        d="M38.2 37.7H24.8L17 51h27.2l-6-13.3z"
        fill="#50E6FF"
      />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg
      className="logout-icon"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M14 4H6C4.9 4 4 4.9 4 6V18C4 19.1 4.9 20 6 20H14"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />

      <path
        d="M11 12H21"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />

      <path
        d="M18 9L21 12L18 15"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PageLayout({ children }) {
  return (
    <div className="app-shell">

      {/* HEADER */}
      <header className="top-header">

        <div className="brand">
          <AzureLogo />

          <span className="brand-name">
            Azure Automation Workflow
          </span>
        </div>

        <button
          className="logout-button"
          type="button"
          aria-label="Logout"
        >
          <LogoutIcon />
        </button>

      </header>

      {/* PAGE */}
      <div className="page-content">
        {children}
      </div>

      {/* FOOTER */}
      <footer className="app-footer">
        Workflow Wizard v1.0 | Cloud Integration
      </footer>

    </div>
  );
}

export default PageLayout;