"""The pinned H5 runtime is available only through the explicit local profile."""

import unittest
from unittest.mock import patch

from backend.app import main


class LocalResearchProfileTests(unittest.TestCase):
    def test_h5_runtime_is_rejected_without_the_explicit_profile(self):
        with patch.multiple(main, LOCAL_RESEARCH_PROFILE=False, MODEL_RUNTIME="h5"):
            with self.assertRaisesRegex(RuntimeError, "explicit local H5 research profile"):
                main.validate_local_research_profile("local-accounts")

    def test_pinned_profile_is_valid_only_for_development_local_accounts_and_h5(self):
        with patch.multiple(
            main,
            LOCAL_RESEARCH_PROFILE=True,
            APP_ENV="development",
            MODEL_RUNTIME="h5",
            H5_CONTRACT_SHA256=main.LOCAL_RESEARCH_H5_CONTRACT_SHA256,
        ):
            main.validate_local_research_profile("local-accounts")

    def test_profile_rejects_runtime_environment_auth_or_contract_mismatch(self):
        invalid_configs = [
            {"APP_ENV": "production", "MODEL_RUNTIME": "h5", "H5_CONTRACT_SHA256": main.LOCAL_RESEARCH_H5_CONTRACT_SHA256},
            {"APP_ENV": "development", "MODEL_RUNTIME": "stub", "H5_CONTRACT_SHA256": main.LOCAL_RESEARCH_H5_CONTRACT_SHA256},
            {"APP_ENV": "development", "MODEL_RUNTIME": "h5", "H5_CONTRACT_SHA256": "0" * 64},
        ]
        for config in invalid_configs:
            with self.subTest(config=config), patch.multiple(
                main,
                LOCAL_RESEARCH_PROFILE=True,
                APP_ENV=config["APP_ENV"],
                MODEL_RUNTIME=config["MODEL_RUNTIME"],
                H5_CONTRACT_SHA256=config["H5_CONTRACT_SHA256"],
            ):
                with self.assertRaisesRegex(RuntimeError, "local H5 research profile"):
                    main.validate_local_research_profile("local-accounts")

    def test_profile_rejects_nonlocal_authentication(self):
        with patch.multiple(
            main,
            LOCAL_RESEARCH_PROFILE=True,
            APP_ENV="development",
            MODEL_RUNTIME="h5",
            H5_CONTRACT_SHA256=main.LOCAL_RESEARCH_H5_CONTRACT_SHA256,
        ):
            with self.assertRaisesRegex(RuntimeError, "local H5 research profile"):
                main.validate_local_research_profile("cloudflare-access")


if __name__ == "__main__":
    unittest.main()
