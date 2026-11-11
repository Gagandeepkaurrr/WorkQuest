from app.engine.registry import CONTENT, load_scenario
from app.engine.validation import validate_scenario


def main():
    passed = True
    for path in sorted(CONTENT.glob("*/scenario.json")):
        report = validate_scenario(load_scenario(path.parent.name).model_dump())
        print(
            f"{path.parent.name}: {'PASS' if report.passed else 'FAIL'}; score={report.golden_score}, t={report.golden_time}"
        )
        for error in report.errors:
            print("  " + error)
        passed = passed and report.passed
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
