"""
Generate synthetic scam/spam labeled data in Urdu and Roman-Urdu.

Creates template-based scam examples covering common patterns:
  - Job scams (fake offers, processing fees)
  - Prize/lottery scams
  - Phishing (bank/account verification)
  - Investment scams (crypto, double money)
  - Fake charity / donation scams

Output: data/raw/synthetic_scam.csv with columns: text, label (1=scam)
"""

import argparse
import csv
import random
from pathlib import Path


_ROMAN_TEMPLATES = [
    # Job scams
    "job available {amount} per week ghar bethy kam karein send processing fee {fee}",
    "online job opportunity {amount} daily earn karein abhi apply karein",
    "data entry job {amount} per month sirf {hours} ghante daily whatsapp karein",
    "work from home {amount} weekly income no experience needed registration fee {fee}",
    "urgent hiring {amount} per day simple typing job advance fee {fee} bhejein",
    "freelance job offer {amount} per project registration k liye {fee} pay karein",
    "part time job {amount} monthly sirf mobile se kam karein fee {fee}",
    "amazon flipkart job {amount} per week ghar se kam product review karein",
    "youtube video dekh ke {amount} daily kamayein registration fee {fee}",
    "typing job available {amount} per page accuracy bonus advance {fee} bhejein",

    # Prize/lottery scams
    "mubarak ho aap ne {amount} ki lottery jeet li hai claim k liye {fee} bhejein",
    "congratulations you won {amount} prize click link to claim now",
    "aap ka number lucky draw mein nikla hai {amount} prize claim karein",
    "free iphone jeetny k liye link click karein aur {fee} pay karein",
    "samsung galaxy free giveaway aap selected hue hain {fee} shipping charge",
    "aap ne {amount} ka inaam jeeta hai processing fee {fee} jama karwayein",
    "lucky winner {amount} cash prize receive karny k liye details bhejein",
    "breaking news aap ko {amount} ka inaam mila hai verify k liye call karein",

    # Phishing / bank scams
    "your bank account will block in 24 hours verify now click link",
    "aap ka bank account suspend ho gaya hai verify k liye ye link kholain",
    "urgent atm card block ho gaya hai update k liye {phone} pe call karein",
    "sbi bank alert aap ka account hack ho gaya hai turant verify karein",
    "jazzcash account mein masla ho gaya hai helpline {phone} pe rabta karein",
    "easypaisa aap ka account limit cross ho gaya verify karein warna block",
    "aap ki debit card information expire ho rahi hai update k liye click karein",
    "kyc verification pending hai {hours} ghante mein complete karein warna account band",

    # Investment scams
    "bitcoin investment {amount} lagayein {days} din mein double ho jaye ga",
    "crypto trading se {amount} daily profit kamayein guaranteed returns",
    "online business start karein sirf {fee} invest karein {amount} monthly return",
    "forex trading {amount} weekly profit hamare expert team ke saath",
    "mutual fund scheme {amount} invest karein {rate}% monthly return guaranteed",
    "real estate investment {amount} se shuru {days} din mein {amount2} return",
    "gold trading platform {amount} daily earn karein no risk full guarantee",

    # Fake charity
    "ramzan donation {amount} dein aur sawab kamayein is number pe bhejein",
    "flood victims ki madad k liye {amount} donate karein is account mein",
    "orphanage donation drive {fee} se shuru karein apni zakat yahan dein",
    "emergency relief fund {amount} contribute karein earthquake victims k liye",

    # Shopping scams
    "mega sale original iphone sirf {amount} mein limited stock abhi order karein",
    " branded shoes {amount} mein original quality cash on delivery nahi advance {fee}",
    "imported cosmetics {amount} mein discounted price payment pehle karein",
    "online shopping {amount} ki purchase pe free gift claim karein shipping {fee}",

    # Loan scams
    "instant loan approval {amount} tak bina kisi document k processing fee {fee}",
    "personal loan {amount} sirf 5 minute mein approval fee {fee} advance",
    "home loan {amount} lowest interest rate processing charge {fee} abhi apply karein",
    "business loan {amount} guaranteed approval documentation fee {fee} pehle dein",
]

_URDU_TEMPLATES = [
    "نوکری دستیاب ہے {amount} ہفتہ وار گھر بیٹھے کام کریں پروسیسنگ فیس {fee} بھیجیں",
    "آن لائن کمائی {amount} روزانہ ابھی رجسٹریشن کریں فیس {fee}",
    "مبارک ہو آپ نے {amount} کی لاٹری جیت لی ہے کلیم کے لیے {fee} بھیجیں",
    "آپ کا بینک اکاؤنٹ بلاک ہو جائے گا ابھی ویریفائی کریں",
    "بٹ کوائن سرمایہ کاری {amount} لگائیں {days} دن میں ڈبل ہو جائے گا",
    "فری آئی فون جیتنے کے لیے لنک کلک کریں اور {fee} ادا کریں",
    "فوری لون {amount} تک بغیر کسی دستاویز کے پروسیسنگ فیس {fee}",
    "ایزی پیسہ اکاؤنٹ میں مسئلہ ہو گیا ہے ہیلپ لائن {phone} پر رابطہ کریں",
    "آن لائن جاب {amount} ماہانہ صرف موبائل سے کام کریں فیس {fee}",
    "کرپٹو ٹریڈنگ سے {amount} یومیہ منافع کمائیں گارنٹیڈ ریٹرنز",
    "سیمسنگ گلیکسی فری گیو اوے آپ سلیکٹ ہوئے ہیں {fee} شپنگ چارج",
    "ڈیبٹ کارڈ معلومات ختم ہو رہی ہے اپ ڈیٹ کے لیے کلک کریں",
    "رمضان ڈونیشن {amount} دیں اور ثواب کمائیں اس نمبر پر بھیجیں",
    "میگا سیل اصل آئی فون صرف {amount} میں محدود سٹاک ابھی آرڈر کریں",
    "ذاتی لون {amount} صرف پانچ منٹ میں اپروول فیس {fee} ایڈوانس",
]

_AMOUNTS = ["5000", "10000", "15000", "20000", "25000", "30000", "50000", "75000", "100000", "500000"]
_FEES = ["500", "999", "1000", "1500", "2000", "2500", "3000", "5000"]
_HOURS = ["2", "3", "4", "5"]
_DAYS = ["7", "10", "15", "30"]
_RATES = ["10", "15", "20", "25", "30"]
_PHONES = ["0300-1234567", "0321-9876543", "0345-5551234", "+92-300-1234567"]


def _fill_template(template: str) -> str:
    replacements = {
        "{amount}": random.choice(_AMOUNTS),
        "{amount2}": random.choice(_AMOUNTS),
        "{fee}": random.choice(_FEES),
        "{hours}": random.choice(_HOURS),
        "{days}": random.choice(_DAYS),
        "{rate}": random.choice(_RATES),
        "{phone}": random.choice(_PHONES),
    }
    result = template
    for key, val in replacements.items():
        result = result.replace(key, val)
    return result


def generate_scam_data(n_samples: int = 1500, seed: int = 42) -> list[dict]:
    random.seed(seed)
    rows = []

    n_roman = int(n_samples * 0.7)
    n_urdu = n_samples - n_roman

    for _ in range(n_roman):
        template = random.choice(_ROMAN_TEMPLATES)
        text = _fill_template(template)
        rows.append({"text": text, "label": 1})

    for _ in range(n_urdu):
        template = random.choice(_URDU_TEMPLATES)
        text = _fill_template(template)
        rows.append({"text": text, "label": 1})

    random.shuffle(rows)
    return rows


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/raw/synthetic_scam.csv")
    parser.add_argument("--n_samples", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--merge_into",
        default=None,
        help="If set, append scam rows to this existing CSV.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    rows = generate_scam_data(args.n_samples, args.seed)

    import pandas as pd

    scam_df = pd.DataFrame(rows)
    scam_df.to_csv(args.output, index=False)
    print(f"Generated {len(rows)} scam examples -> {args.output}")

    if args.merge_into:
        import pandas as pd
        existing = pd.read_csv(args.merge_into)
        merged = pd.concat([existing, scam_df], ignore_index=True)
        merged = merged.drop_duplicates(subset=["text"]).sample(frac=1, random_state=42)
        merged.to_csv(args.merge_into, index=False)
        print(f"Merged into {args.merge_into}: {len(merged)} total rows")


if __name__ == "__main__":
    main()
