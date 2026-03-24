"""
# list all 
sqlh list --all -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319

sqlh list --all -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319 --output-format text

# list root
sqlh list --root -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319

sqlh list --root -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319 --output-format text

# list leaf
sqlh list --leaf -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319 --output-format text


# search root
sqlh search --root -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319 \
    --table dws.dws_cy_cust_ltst_active_rec \
    --output-format web

# search all
sqlh search --all -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319 \
    --table dim.dim_shopinfo \
    --output-format text

# search upstream
sqlh search --upstream -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319 \
    --table ods.ods_plr_dwm_hr_cy_p7 \
    --output-format text

# search downstream
sqlh search --downstream -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319 \
    --table ods.ods_plr_dwm_hr_cy_p7 \
    --output-format web


# web
sqlh web -p /Users/dunett/codes/duperl/daas-migration/showyu_llm_backup_20260319
"""