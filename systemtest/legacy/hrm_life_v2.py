"""
Legacy HRM life loop entrypoint preserved for reference.
"""
from Systemtest import HRMSystem


def run_hrm_life_v2() -> None:
    """
    Entry point for the hrm-life command.
    Runs the HRM infinite life loop with SelfPurposeEngine integration.
    This function creates an HRMSystem instance and runs its life loop.
    """
    print("=" * 60)
    print("HRM-LIFE: Infinite Loop with Autonomous Goal Discovery")
    print("=" * 60)

    # Use HRMSystem.run_life which has SelfPurposeEngine integrated
    hrm = HRMSystem()
    hrm.run_life()
