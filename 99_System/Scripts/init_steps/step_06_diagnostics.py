"""Step 6: Python Environment Verification and External Integrations Health Check."""

from init_steps.base import BaseInitStep, InitContext, InitStepRegistry

REQUIRED_PACKAGES = [
    ("requests", "requests"),
    ("yaml", "PyYAML"),
    ("pydantic", "pydantic"),
    ("yfinance", "yfinance"),
    ("bs4", "beautifulsoup4"),
    ("rich", "rich"),
    ("xlrd", "xlrd"),
]


def verify_python_dependencies() -> list[str]:
    """Check whether required core Python packages are installed. Returns list of missing package names."""
    missing = []
    for mod_name, pkg_name in REQUIRED_PACKAGES:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        print(f"   ⚠️ Missing Python packages: {', '.join(missing)}")
        print("   Install them using:")
        print(f"   pip install {' '.join(missing)}")
    else:
        print("   ✓ All required core Python packages are installed.")
    return missing


@InitStepRegistry.register
class DiagnosticsStep(BaseInitStep):
    """Step 6: Check Python dependencies and optionally run external integration health checks."""

    step_id = "diagnostics"
    step_number = 6
    title = "Checking Python dependencies & testing external integrations"
    description = "Verify required Python packages and optionally run integration connectivity diagnostics."
    aliases = ["health", "check", "deps"]

    def run(self, ctx: InitContext) -> bool:
        self.print_header(single_step=ctx.single_step_mode)

        verify_python_dependencies()

        run_diagnostics = False
        if ctx.interactive:
            try:
                choice = (
                    input("   Would you like to test external connectivity & integrations now? [Y/n]: ").strip().lower()
                )
                run_diagnostics = choice in ("", "y", "yes")
            except (EOFError, KeyboardInterrupt):
                run_diagnostics = False

        if run_diagnostics:
            from health_check import run_health_check

            try:
                report, _ = run_health_check(
                    target_vault=ctx.target_dir,
                    write_markdown=True,
                )
                print(f"   ✓ Health check completed ({report.passed_count}/{len(report.results)} services OK).")
            except Exception as e:
                print(f"   ⚠️ Health check encountered an error: {e}")
        else:
            print("   Skipped diagnostic check. You can run it anytime with 'python run.py --health'.")

        return True
