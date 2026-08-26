# Landscape digest — round 1

## Findings

- **Face blurring is a baseline redaction, not a complete video anonymization
  claim.** The ICO treats video footage as qualitative/unstructured material
  requiring data-specific techniques; it names blurring or masking faces and
  other identifying information, disguising/re-recording audio, and removing
  direct and indirect identifiers as possible measures. It also says
  identifiability depends on singling out, linkability, context, available
  outside information, and the motivated intruder—not only whether a name is
  visible. (Publisher: UK Information Commissioner's Office; accessed
  2026-08-26; confidence: high; class: privacy guidance.)
  Source: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/anonymisation/how-do-we-ensure-anonymisation-is-effective/

- **Face obfuscation can change action-recognition utility.** A CVPR
  workshop study evaluated face blurring in video classification and reported a
  larger performance effect than in image classification; it proposed training
  with privileged face information to close that gap. This supports measuring
  action utility on the transformed representation rather than assuming face
  blur is behavior-preserving. (Publisher: Computer Vision Foundation; 2021;
  accessed 2026-08-26; confidence: medium; class: utility evidence.)
  Source: https://openaccess.thecvf.com/content/CVPR2021W/TCV/html/Tomei_Estimating_and_Fixing_the_Effect_of_Face_Obfuscation_in_Video_CVPRW_2021_paper.html

- **Pose/skeleton representations reduce raw-pixel exposure but are not
  automatically anonymous.** Research on skeleton action recognition reports
  that actor re-identification and sensitive-attribute classifiers can use
  skeleton trajectories; later work identifies body proportions and motion
  style, including gait and posture transitions, as privacy-relevant signals.
  (Publishers: arXiv and Computer Vision Foundation; 2021–2025; accessed
  2026-08-26; confidence: medium; class: privacy attack evidence.)
  Sources:
  - https://arxiv.org/abs/2111.15129
  - https://openaccess.thecvf.com/content/ICCV2025/papers/Carr_Privacy-centric_Deep_Motion_Retargeting_for_Anonymization_of_Skeleton-Based_Motion_Visualization_ICCV2025_paper.pdf

- **Learned privacy-preserving action recognition is a research option, not a
  first implementation dependency.** SPAct, STPrivacy, and related work
  formulate the problem as a utility/privacy trade-off and train an
  anonymization transform against privacy attacks while preserving action
  performance. STPrivacy specifically argues that frame-only privacy
  handling can miss temporal leakage and evaluates attacks over complete
  videos. (Publishers: Computer Vision Foundation; 2022–2023; accessed
  2026-08-26; confidence: medium; class: research landscape.)
  Sources:
  - https://openaccess.thecvf.com/content/CVPR2022/html/Dave_SPAct_Self-Supervised_Privacy_Preservation_for_Action_Recognition_CVPR_2022_paper.html
  - https://openaccess.thecvf.com/content/ICCV2023/html/Li_STPrivacy_Spatio-Temporal_Privacy-Preserving_Action_Recognition_ICCV2023_paper.html

## Leads and gaps

- Compare pose-only output with pose retargeting or normalization before
  treating keypoints as a retained artifact.
- Define whether the product needs human-readable video review, machine action
  recognition, or both; that determines whether redacted RGB video is needed.
- Check audio, subtitles, embedded metadata, background text, and multi-person
  tracking as separate privacy channels.
- No evidence in this round establishes a universal de-identification
  guarantee for any of these representations.
