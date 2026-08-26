"""Android App Links proof, configured from the release signing certificate."""

from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(tags=["mobile-links"])


@router.get("/.well-known/assetlinks.json")
async def asset_links() -> list[dict]:
    fingerprints = [
        value.strip().upper()
        for value in settings.android_app_link_sha256.split(",")
        if value.strip()
    ]
    if not fingerprints:
        raise HTTPException(404, "Android App Links are not configured")
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "com.shoots.app",
                "sha256_cert_fingerprints": fingerprints,
            },
        }
    ]
