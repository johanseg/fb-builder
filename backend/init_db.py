from app.database import engine, Base, SessionLocal
from app.models import *
from app.core.security import get_password_hash

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

def seed_roles_and_permissions():
    """Seed default roles and permissions"""
    db = SessionLocal()
    try:
        # Define default permissions
        default_permissions = [
            ("brands:read", "View brands"),
            ("brands:write", "Create and edit brands"),
            ("brands:delete", "Delete brands"),
            ("products:read", "View products"),
            ("products:write", "Create and edit products"),
            ("products:delete", "Delete products"),
            ("ads:read", "View ads"),
            ("ads:write", "Create and edit ads"),
            ("ads:delete", "Delete ads"),
            ("campaigns:read", "View campaigns"),
            ("campaigns:write", "Create and edit campaigns"),
            ("campaigns:delete", "Delete campaigns"),
            ("templates:read", "View templates"),
            ("templates:write", "Create and edit templates"),
            ("templates:delete", "Delete templates"),
            ("users:read", "View users"),
            ("users:write", "Manage users"),
            ("research:read", "View research data"),
            ("research:write", "Create searches and manage blacklists"),
            ("research:admin", "Run scheduled searches"),
        ]

        # Create permissions if they don't exist
        permissions = {}
        for name, description in default_permissions:
            existing = db.query(Permission).filter(Permission.name == name).first()
            if not existing:
                perm = Permission(name=name, description=description)
                db.add(perm)
                db.flush()
                permissions[name] = perm
                print(f"  Created permission: {name}")
            else:
                permissions[name] = existing

        # Define default roles with their permissions
        default_roles = {
            "admin": {
                "description": "Full access to all resources",
                "permissions": list(permissions.keys())
            },
            "manager": {
                "description": "Can manage brands, products, ads, and campaigns",
                "permissions": [
                    "brands:read", "brands:write",
                    "products:read", "products:write",
                    "ads:read", "ads:write",
                    "campaigns:read", "campaigns:write",
                    "templates:read", "templates:write",
                    "research:read", "research:write",
                ]
            },
            "editor": {
                "description": "Can create and edit ads and templates",
                "permissions": [
                    "brands:read",
                    "products:read",
                    "ads:read", "ads:write",
                    "templates:read", "templates:write",
                    "research:read", "research:write",
                ]
            },
            "viewer": {
                "description": "Read-only access",
                "permissions": [
                    "brands:read",
                    "products:read",
                    "ads:read",
                    "campaigns:read",
                    "templates:read",
                    "research:read",
                ]
            }
        }

        # Create roles if they don't exist
        for role_name, role_data in default_roles.items():
            existing = db.query(Role).filter(Role.name == role_name).first()
            if not existing:
                role = Role(name=role_name, description=role_data["description"])
                # Add permissions to role
                for perm_name in role_data["permissions"]:
                    if perm_name in permissions:
                        role.permissions.append(permissions[perm_name])
                db.add(role)
                print(f"  Created role: {role_name}")
            else:
                print(f"  Role exists: {role_name}")

        db.commit()
        print("Roles and permissions seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding roles and permissions: {e}")
        raise
    finally:
        db.close()

def create_superuser(email: str, password: str, name: str = "Admin"):
    """Create a superuser if one doesn't exist"""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User {email} already exists")
            return

        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            name=name,
            is_superuser=True,
            is_active=True
        )

        # Add admin role
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            user.roles.append(admin_role)

        db.add(user)
        db.commit()
        print(f"Superuser {email} created successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error creating superuser: {e}")
        raise
    finally:
        db.close()

def seed_default_brand():
    """Seed the default Townsquare Interactive brand and product"""
    db = SessionLocal()
    try:
        existing = db.query(Brand).filter(Brand.name == "Townsquare Interactive").first()
        if existing:
            print("  Default brand already exists: Townsquare Interactive")
            return

        brand = Brand(
            name="Townsquare Interactive",
            voice="Credible, practical, confident, grounded, specific, clear, performance-minded, local-business fluent. Never overhyped, never bro marketing, never fluffy agency jargon.",
            primary_color="#F59E0B",
            secondary_color="#D97706",
            highlight_color="#FBBF24",
        )
        db.add(brand)
        db.flush()

        product = Product(
            brand_id=brand.id,
            name="Local Marketing & Digital Presence",
            description="Done-for-you local marketing execution: website presence, local SEO, Google Business Profile optimization, blog/content support, local search visibility, CRM, email/SMS marketing, online bookings, payments, and lead capture tools. Built for established local businesses that already do good work offline but are invisible, inconsistent, or weak online.",
            pain_points=[
                "Invisible online despite doing great work offline",
                "Losing customers to competitors with better digital presence",
                "Wasting money on marketing that doesn't generate measurable leads",
                "No time to manage website, social media, and online listings",
                "Inconsistent brand presence across Google, Facebook, and directories"
            ],
            desired_outcomes=[
                "Show up first when locals search for their services",
                "Consistent stream of qualified leads from online channels",
                "Professional digital presence that matches their real-world reputation",
                "More time running their business instead of figuring out marketing",
                "Clear ROI visibility on every marketing dollar spent"
            ],
            root_causes=[
                "Local businesses lack the time and expertise to manage digital marketing",
                "DIY marketing tools are overwhelming and produce mediocre results",
                "Most agencies overpromise and underdeliver with vague metrics",
                "Google and Facebook algorithms change constantly, requiring dedicated attention",
                "Disconnected tools create fragmented customer experiences"
            ],
            proof_points=[
                "Serving thousands of local businesses across the US",
                "Dedicated local marketing specialists assigned to each account",
                "Proprietary technology platform built specifically for local business needs",
                "Measurable results with transparent monthly performance reporting",
                "Part of Townsquare Media with deep local market expertise"
            ],
            differentiators=[
                "All-in-one platform replacing 5-7 separate marketing tools",
                "Local market specialists who understand small business challenges",
                "Done-for-you execution, not another DIY tool to learn",
                "Transparent pricing with no long-term contracts",
                "Performance-based approach with real ROI tracking"
            ],
            risk_reversals=[
                "No long-term contracts — month-to-month flexibility",
                "Dedicated account manager you can actually reach",
                "Transparent reporting so you see exactly what you're paying for",
                "Free initial consultation and digital presence audit",
                "Cancel anytime if you're not seeing results"
            ],
        )
        db.add(product)
        db.commit()
        print("  Created default brand: Townsquare Interactive")
        print("  Created default product: Local Marketing & Digital Presence")

    except Exception as e:
        db.rollback()
        print(f"Error seeding default brand: {e}")
    finally:
        db.close()


def backfill_product_brief():
    """Backfill pain_points and other brief fields on existing products that are missing them."""
    db = SessionLocal()
    try:
        products = db.query(Product).filter(Product.pain_points.is_(None)).all()
        if not products:
            print("  All products already have brief data")
            return

        default_brief = {
            "pain_points": [
                "Invisible online despite doing great work offline",
                "Losing customers to competitors with better digital presence",
                "Wasting money on marketing that doesn't generate measurable leads",
                "No time to manage website, social media, and online listings",
                "Inconsistent brand presence across Google, Facebook, and directories"
            ],
            "desired_outcomes": [
                "Show up first when locals search for their services",
                "Consistent stream of qualified leads from online channels",
                "Professional digital presence that matches their real-world reputation",
                "More time running their business instead of figuring out marketing",
                "Clear ROI visibility on every marketing dollar spent"
            ],
            "root_causes": [
                "Local businesses lack the time and expertise to manage digital marketing",
                "DIY marketing tools are overwhelming and produce mediocre results",
                "Most agencies overpromise and underdeliver with vague metrics",
                "Google and Facebook algorithms change constantly, requiring dedicated attention",
                "Disconnected tools create fragmented customer experiences"
            ],
            "proof_points": [
                "Serving thousands of local businesses across the US",
                "Dedicated local marketing specialists assigned to each account",
                "Proprietary technology platform built specifically for local business needs",
                "Measurable results with transparent monthly performance reporting",
                "Part of Townsquare Media with deep local market expertise"
            ],
            "differentiators": [
                "All-in-one platform replacing 5-7 separate marketing tools",
                "Local market specialists who understand small business challenges",
                "Done-for-you execution, not another DIY tool to learn",
                "Transparent pricing with no long-term contracts",
                "Performance-based approach with real ROI tracking"
            ],
            "risk_reversals": [
                "No long-term contracts — month-to-month flexibility",
                "Dedicated account manager you can actually reach",
                "Transparent reporting so you see exactly what you're paying for",
                "Free initial consultation and digital presence audit",
                "Cancel anytime if you're not seeing results"
            ],
        }

        for product in products:
            for field, value in default_brief.items():
                setattr(product, field, value)
            print(f"  Backfilled brief data for product: {product.name}")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error backfilling product brief: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("\nSeeding roles and permissions...")
    seed_roles_and_permissions()

    # Seed default Townsquare Interactive brand
    print("\nSeeding default brand...")
    seed_default_brand()

    # Backfill product brief data on existing products
    print("\nBackfilling product brief data...")
    backfill_product_brief()

    # Optionally create a default superuser (requires env vars)
    import os
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        print(f"\nCreating superuser ({admin_email})...")
        create_superuser(admin_email, admin_password)
    else:
        print("\nSkipping superuser creation (set ADMIN_EMAIL and ADMIN_PASSWORD to create one)")
