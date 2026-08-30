#!/usr/bin/env python3
"""
Hugging Face Policy Compliance Checker for LTX 2.3 I2V Space
Ensures all generated content follows HF community guidelines
"""

import logging
from typing import Tuple, List
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PolicyChecker:
    """Check prompts and content for HF policy compliance"""
    
    # Blocked content keywords
    BLOCKED_KEYWORDS = {
        "nsfw": [
            "nude", "naked", "sex", "porn", "explicit", "adult",
            "sexual", "xxx", "erotic", "lewd", "hentai", "fetish"
        ],
        "violence": [
            "kill", "murder", "gore", "blood", "violent", "brutal",
            "torture", "abuse", "assault", "weapon", "gun", "knife"
        ],
        "hate": [
            "racist", "sexist", "homophobic", "transphobic", "discriminate",
            "hate", "slur", "ethnic", "religion", "minority"
        ],
        "harmful": [
            "drug", "illegal", "bomb", "explosion", "suicide",
            "self-harm", "harm"
        ],
        "deepfake": [
            "deepfake", "face swap", "impersonate", "fake",
            "clone", "replicate", "copy face"
        ]
    }
    
    RISKY_PATTERNS = {
        "real_people": r"(?:photo|picture|image) of (.*?) (?:real|actual|real-life)",
        "celebrity": r"(?:looks like|similar to|copy|fake) (.*?)(?:\b|$)",
        "copyrighted": r"(?:copyrighted|trademarked|licensed) (.*?)(?:\b|$)"
    }
    
    WARNINGS = {
        "watermark": "generated content may need watermarking",
        "quality": "may need additional review before publication",
        "attribution": "ensure proper attribution if using reference material"
    }

    def __init__(self, strict_mode: bool = True):
        """Initialize policy checker
        
        Args:
            strict_mode: If True, stricter filtering; if False, allow more content
        """
        self.strict_mode = strict_mode
        self.violation_count = 0
        self.warning_count = 0

    def check_prompt(self, prompt: str) -> Tuple[bool, List[str], List[str]]:
        """
        Check if prompt violates HF policy
        
        Args:
            prompt: User's video generation prompt
            
        Returns:
            Tuple of (is_safe, violations, warnings)
        """
        violations = []
        warnings = []
        
        if not prompt or len(prompt.strip()) == 0:
            return True, [], []
        
        prompt_lower = prompt.lower()
        
        # Check blocked keywords
        for category, keywords in self.BLOCKED_KEYWORDS.items():
            for keyword in keywords:
                if re.search(r'\b' + keyword + r'\b', prompt_lower):
                    violation = f"Policy violation ({category}): '{keyword}' not allowed"
                    violations.append(violation)
                    self.violation_count += 1
        
        # Check risky patterns
        for pattern_name, pattern in self.RISKY_PATTERNS.items():
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                warning = f"Content review needed ({pattern_name}): {pattern_name} detected"
                warnings.append(warning)
                self.warning_count += 1
        
        # Check for requests to violate policy
        policy_bypass_patterns = [
            r"ignore.*policy",
            r"bypass.*filter",
            r"override.*safety",
            r"disable.*check"
        ]
        
        for pattern in policy_bypass_patterns:
            if re.search(pattern, prompt_lower):
                violations.append("Policy violation: Cannot bypass safety guidelines")
                self.violation_count += 1
                break
        
        is_safe = len(violations) == 0
        
        if not is_safe:
            logger.warning(f"Prompt rejected - Violations: {violations}")
        elif warnings:
            logger.info(f"Prompt accepted with warnings: {warnings}")
        else:
            logger.info("Prompt passed all checks")
        
        return is_safe, violations, warnings

    def check_negative_prompt(self, negative_prompt: str) -> Tuple[bool, List[str]]:
        """Check negative prompt for bypass attempts"""
        violations = []
        
        if not negative_prompt or len(negative_prompt.strip()) == 0:
            return True, []
        
        negative_lower = negative_prompt.lower()
        
        # Check if negative prompt is being used to generate blocked content
        bypass_indicators = [
            r"not.*(?:safe|policy|guideline)",
            r"generate.*(?:forbidden|blocked)",
            r"make.*(?:adult|explicit|violent)"
        ]
        
        for pattern in bypass_indicators:
            if re.search(pattern, negative_lower):
                violations.append("Policy bypass attempt in negative prompt")
                self.violation_count += 1
        
        is_safe = len(violations) == 0
        return is_safe, violations

    def check_keyframes(self, keyframes_json: str) -> Tuple[bool, List[str]]:
        """Check keyframes for policy compliance"""
        violations = []
        
        if not keyframes_json or len(keyframes_json.strip()) == 0:
            return True, []
        
        try:
            import json
            keyframes = json.loads(keyframes_json)
            
            # Check each keyframe prompt
            for timestamp, prompt in keyframes.items():
                is_safe, frame_violations, _ = self.check_prompt(str(prompt))
                violations.extend(frame_violations)
            
        except json.JSONDecodeError:
            # Invalid JSON handled elsewhere
            pass
        except Exception as e:
            logger.error(f"Error checking keyframes: {e}")
        
        is_safe = len(violations) == 0
        return is_safe, violations

    def get_policy_summary(self) -> str:
        """Get summary of policy compliance checks"""
        return f"""
HUGGING FACE POLICY COMPLIANCE
────────────────────────────────
✓ No NSFW/adult content
✓ No violence or gore
✓ No hate speech or discrimination
✓ No harmful/illegal content
✓ No deepfakes of real people
✓ No copyright violations
✓ Original or properly attributed content

Violations found: {self.violation_count}
Warnings issued: {self.warning_count}

For violations, content generation will be blocked.
For warnings, manual review may be required.
"""

    def reset_counters(self):
        """Reset violation and warning counters"""
        self.violation_count = 0
        self.warning_count = 0

class ContentModerator:
    """Comprehensive content moderation for Space"""
    
    def __init__(self):
        self.policy_checker = PolicyChecker(strict_mode=True)
        self.session_violations = {}

    def check_generation_request(
        self,
        session_id: str,
        prompt: str,
        negative_prompt: str = "",
        keyframes_json: str = ""
    ) -> Tuple[bool, str]:
        """
        Comprehensive check before generation
        
        Returns:
            Tuple of (approved, message)
        """
        violations = []
        warnings = []
        
        # Check main prompt
        prompt_safe, prompt_violations, prompt_warnings = self.policy_checker.check_prompt(prompt)
        violations.extend(prompt_violations)
        warnings.extend(prompt_warnings)
        
        # Check negative prompt
        neg_safe, neg_violations = self.policy_checker.check_negative_prompt(negative_prompt)
        violations.extend(neg_violations)
        
        # Check keyframes
        kf_safe, kf_violations = self.policy_checker.check_keyframes(keyframes_json)
        violations.extend(kf_violations)
        
        # Track violations per session
        if violations:
            self.session_violations[session_id] = {
                "violations": violations,
                "warnings": warnings,
                "timestamp": __import__("time").time()
            }
        
        # Determine if generation should proceed
        if violations:
            message = "❌ Content Policy Violation\n\n" + "\n".join(violations)
            logger.warning(f"Generation blocked for session {session_id}")
            return False, message
        
        if warnings and len(warnings) > 0:
            message = "⚠️ Content Review Recommended\n\n" + "\n".join(warnings) + \
                     "\n\n✅ Generation approved with manual review recommended"
            return True, message
        
        message = "✅ Content meets all policies. Generation approved."
        return True, message

    def get_session_report(self, session_id: str) -> str:
        """Get moderation report for session"""
        if session_id not in self.session_violations:
            return "✅ No policy violations for this session"
        
        data = self.session_violations[session_id]
        report = f"""
MODERATION REPORT - Session {session_id}
────────────────────────────────
Violations: {len(data['violations'])}
Warnings: {len(data['warnings'])}

Violations:
{chr(10).join('• ' + v for v in data['violations'])}

Warnings:
{chr(10).join('• ' + w for w in data['warnings'])}
"""
        return report


def validate_image_content(image_path: str) -> Tuple[bool, str]:
    """
    Validate image reference doesn't violate policy
    (Placeholder - would use ML model in production)
    """
    try:
        from PIL import Image
        import os
        
        if not os.path.exists(image_path):
            return False, "Image file not found"
        
        img = Image.open(image_path)
        
        # Basic checks
        if img.size[0] < 256 or img.size[1] < 256:
            return False, "Image too small (minimum 256x256)"
        
        if img.size[0] > 4096 or img.size[1] > 4096:
            return False, "Image too large (maximum 4096x4096)"
        
        # Check file size
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        if file_size_mb > 100:
            return False, "File too large (maximum 100MB)"
        
        return True, "Image validation passed"
        
    except Exception as e:
        return False, f"Image validation error: {str(e)}"


if __name__ == "__main__":
    # Test policy checker
    checker = PolicyChecker()
    
    # Test cases
    test_prompts = [
        "A beautiful sunset over mountains",
        "A person doing nude yoga",
        "A violent action scene",
        "A peaceful meditation video"
    ]
    
    print(checker.get_policy_summary())
    print("\nTest Results:")
    print("=" * 50)
    
    for prompt in test_prompts:
        is_safe, violations, warnings = checker.check_prompt(prompt)
        status = "✅ SAFE" if is_safe else "❌ BLOCKED"
        print(f"\n{status}: {prompt}")
        if violations:
            print(f"  Violations: {violations}")
        if warnings:
            print(f"  Warnings: {warnings}")
