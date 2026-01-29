import os
import subprocess
from pathlib import Path

from cocotb_tools.runner import get_runner


def test_simple_dff_runner():
    proj_path = Path(__file__).resolve().parent
    rtl_dir = proj_path / "rtl"
    addr_map = proj_path / "addrmap.rdl"

    # first create files
    os.environ.update({"ADDR_MAP": str(addr_map)})

    subprocess.run(
        ["uv", "run", "peakrdl", "sv", "-o", rtl_dir, addr_map],
        check=True,
    )

    subprocess.run(
        ["uv", "run", "sv-exporter", "-o", rtl_dir, "install"],
        check=True,
    )

    # start simulation
    sim = os.getenv("SIM", "icarus")

    sources = [
        rtl_dir / f
        for f in [
            "rdl_subreg_pkg.sv",
            "rdl_subreg_ext.sv",
            "rdl_subreg_flop.sv",
            "rdl_subreg_arb.sv",
            "rdl_subreg.sv",
            "test_reg_pkg.sv",
            "test_reg_top.sv",
        ]
    ]

    print("Simulation sources:")
    for src in sources:
        print(f" - {src}")

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="test_reg_top",
        always=True,
        timescale=("1ns", "1ps"),
        build_dir=proj_path / "sim_build",
    )

    runner.test(
        hdl_toplevel="test_reg_top",
        test_module="test",
        timescale=("1ns", "1ps"),
        build_dir=proj_path / "sim_build",
    )


if __name__ == "__main__":
    test_simple_dff_runner()
