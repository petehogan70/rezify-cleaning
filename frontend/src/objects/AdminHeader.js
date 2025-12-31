import { useNavigate } from "react-router-dom";
import { useTheme } from "../hooks/ThemeContext";
import "../styles/AdminDashboard.css"; // make sure to create this CSS file

export function AdminHeader({ onLogout, loading, onExport }) {
  const navigate = useNavigate();
  const { theme } = useTheme();

  return (
    <div className="header-banner">
      <div className="header-left" onClick={() => navigate("/")}>
        <span className="header-title">Rezify</span>
      </div>

      <div className="header-right">

        <button
          type="button"
          className="admin-header-btn"
          onClick={onExport}
          title={'Export all data as CSV'}
        >
          Export Data
        </button>


        <a
          href="https://docs.google.com/forms/d/e/1FAIpQLScO906_cFeHxCN_3UdPhA8FckpcUWxMFfcNn5wCstICRnv52Q/viewform?usp=header"
          target="_blank"
          rel="noreferrer"
          className="admin-header-btn"
        >
          Request New Admin
        </a>

        <a
          href="https://docs.google.com/forms/d/e/1FAIpQLSc-k4IwTBVefPbjab2qrEIpWmbZY2ZUmueSdGf_k5K2C3Dgkg/viewform?usp=dialog"
          target="_blank"
          rel="noreferrer"
          className="admin-header-btn"
        >
          Help
        </a>

        <a
          href="https://docs.google.com/forms/d/e/1FAIpQLScNkHif1i5g55QJ71kJ_XWLVhlP5g7-XmW7LnGscsjtZzM86A/viewform?usp=dialog"
          target="_blank"
          rel="noreferrer"
          className="admin-header-btn"
        >
          Feedback
        </a>

        <div className="header-divider"></div>

        <button
          type="button"
          className="admin-header-btn"
          onClick={onLogout}
          disabled={loading}
          title={loading ? 'Logging out...' : 'Log out'}
        >
          Logout
        </button>

      </div>
    </div>
  );
}
