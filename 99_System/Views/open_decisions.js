/**
 * Shared DataviewJS View: Open Decisions List
 *
 * Parameters passed via `input`:
 *   - portfolio: (Optional) "Safety net", "Long term", "Aggressive", or null (for all)
 *   - status: (Optional) Filter by status (default: "open")
 *
 * Usage:
 *   await dv.view("99_System/Views/open_decisions", { portfolio: "Aggressive" });
 */

let targetPortfolio = input?.portfolio ? String(input.portfolio).toLowerCase().trim() : null;
let targetStatus = input?.status ? String(input.status).toLowerCase().trim() : "open";

let decisions = dv.pages('"20_Decisions"')
    .where(p => p.type === "decision")
    .where(p => (p.status || "").toLowerCase().trim() === targetStatus);

if (targetPortfolio && targetPortfolio !== "all") {
    decisions = decisions.where(p => {
        let port = (p.portfolio || "").toLowerCase().trim();
        let targetPort = (p.target_portfolio || "").toLowerCase().trim();

        if (targetPortfolio === "safety net" || targetPortfolio === "safety") {
            return port.includes("safety") || targetPort.includes("safety");
        } else if (targetPortfolio === "long term" || targetPortfolio === "long_term") {
            return port.includes("long") || targetPort.includes("long");
        } else if (targetPortfolio === "aggressive") {
            return port.includes("aggressive") || targetPort.includes("aggressive");
        }
        return port === targetPortfolio || targetPort === targetPortfolio;
    });
}

decisions = decisions.sort(p => p.date, 'desc');

function formatActionBadge(action) {
    let act = String(action || "").toUpperCase().trim();
    if (act === "BUY") return "🟢 **BUY**";
    if (act === "SELL") return "🔴 **SELL**";
    if (act === "TRIM") return "🟠 **TRIM**";
    if (act === "ADD") return "🔵 **ADD**";
    return `**${act || "-"}**`;
}

function formatPortfolioName(title) {
    if (!title) return "Consolidated Portfolio";
    let t = title.toLowerCase();
    if (t.includes("safety")) return "Safety Net";
    if (t.includes("long")) return "Long Term";
    if (t.includes("aggressive")) return "Aggressive";
    return title;
}

let displayName = formatPortfolioName(input?.portfolio);

if (decisions.length === 0) {
    dv.paragraph(`> [!NOTE] 📋 **Open Decisions:** No pending decisions for **${displayName}**.`);
} else {
    dv.paragraph(`> [!INFO] 📋 **Pending Decisions (${decisions.length}):** Active trades and rebalancing orders requiring execution.`);

    if (!targetPortfolio || targetPortfolio === "all") {
        // Global overview table (includes Portfolio column)
        dv.table(
            ["Decision", "Action", "Portfolio", "Asset", "Platform", "Date"],
            decisions.map(d => {
                let portStr = d.portfolio || "-";
                if (d.target_portfolio) {
                    portStr += ` ➔ ${d.target_portfolio}`;
                }
                return [
                    dv.fileLink(d.file.path, false, d.file.name.replace(/\.md$/, '')),
                    formatActionBadge(d.action),
                    portStr,
                    d.ticker ? dv.fileLink(`10_Finance/Assets/${d.ticker}`, false, d.ticker) : "-",
                    d.platform || "-",
                    d.date || "-"
                ];
            })
        );
    } else {
        // Sub-portfolio specific table
        dv.table(
            ["Decision", "Action", "Asset", "Platform", "Date", "Context / Target"],
            decisions.map(d => {
                let noteContext = "-";
                let port = (d.portfolio || "").toLowerCase().trim();
                let targetP = (d.target_portfolio || "").toLowerCase().trim();

                if (targetP && targetP !== port) {
                    noteContext = `Transfer: ${d.portfolio} ➔ ${d.target_portfolio}`;
                } else if (d.tags && Array.isArray(d.tags)) {
                    noteContext = d.tags.filter(t => t !== "decision").join(", ");
                }

                return [
                    dv.fileLink(d.file.path, false, d.file.name.replace(/\.md$/, '')),
                    formatActionBadge(d.action),
                    d.ticker ? dv.fileLink(`10_Finance/Assets/${d.ticker}`, false, d.ticker) : "-",
                    d.platform || "-",
                    d.date || "-",
                    noteContext || "-"
                ];
            })
        );
    }
}

return decisions;
