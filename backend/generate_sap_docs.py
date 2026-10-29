import sys
from pathlib import Path
import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "knowledge_base" / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Specification for 10 realistic SAP manuals
MANUALS_SPEC = [
    {
        "filename": "SAP_MM_Materials_Management_Manual.pdf",
        "title": "SAP Materials Management (MM) Configuration and User Manual",
        "module": "SAP MM",
        "topics": [
            ("Overview of SAP MM Module", "SAP Materials Management (MM) is a core logistics module that supports the procurement and inventory functions occurring in day-to-day business operations. It covers purchasing, goods receiving, material storage, inventory management, and invoice verification. MM integrates tightly with SAP FI, CO, SD, and PP."),
            ("Organizational Structure in MM", "The MM organizational structure consists of Client, Company Code, Plant, and Storage Location. Purchasing Organization is the organizational unit responsible for procuring materials and services. Purchasing Groups represent buyers or groups of buyers responsible for operational purchasing activities."),
            ("Master Data: Material Master (MARA/MARC)", "The Material Master is the central source of information on materials that can be procured, produced, or sold. Key database tables include MARA for general material data, MARC for plant-specific data, and MARD for storage location data. Material types include ROH (raw materials), HALB (semi-finished), and FERT (finished goods)."),
            ("Master Data: Vendor Master and BP", "In SAP ERP, vendor master data was maintained via transaction FK01/XK01. In SAP S/4HANA, the Business Partner (BP) approach is mandatory. All vendors and suppliers are created as Business Partners with specific roles such as FLVN00 (FI Vendor) and FLVN01 (Purchasing Vendor)."),
            ("Purchasing Requisition (PR)", "Purchase Requisitions are internal documents used to request the purchasing department to procure a material or service. PRs can be generated manually via transaction ME51N or automatically by MRP (Material Requirements Planning) when stock falls below reorder points."),
            ("Purchase Order Processing (ME21N)", "Purchase Orders (POs) represent legally binding requests sent to vendors to deliver goods or services at stated prices. Transaction ME21N is used to create standard POs. Key tables include EKKO for header data and EKPO for line item details. Pricing conditions determine net prices and surcharges."),
            ("Goods Receipt Process (MIGO)", "Goods Receipt (GR) records the physical receipt of goods from a vendor against a purchase order. Transaction MIGO is utilized with movement type 101 (GR for Purchase Order). During GR, inventory valuation accounts are debited and the GR/IR clearing account is credited."),
            ("Invoice Verification (MIRO)", "Logistics Invoice Verification is executed using transaction MIRO. Invoices received from suppliers are verified against the corresponding Purchase Order and Goods Receipt. If tolerances for quantity or price are exceeded, the invoice is blocked for payment."),
            ("The 3-Way Match Verification", "The 3-Way Match is an essential financial control mechanism in SAP MM. It compares three key documents: the Purchase Order (ordered price and quantity), the Goods Receipt (delivered quantity), and the Supplier Invoice (billed price and quantity). All three must align within tolerances to approve payment."),
            ("Inventory Management Movement Types", "Movement types are three-digit numeric keys that distinguish inventory transactions. Common movement types include: 101 for Goods Receipt against PO, 102 for reversal of GR, 201 for Goods Issue to Cost Center, 261 for Goods Issue to Production Order, and 561 for initial stock upload."),
            ("Physical Inventory and Cycle Counting", "SAP MM supports periodic and continuous cycle counting physical inventory methods. Transaction MI01 creates the physical inventory document, MI04 records the counted quantities, and MI07 posts inventory differences to financial accounting."),
            ("Special Procurement: Subcontracting", "Subcontracting involves providing components to an external vendor who manufactures the finished product. Movement type 541 transfers components to subcontracting stock, and movement type 101 (with 543 consumption) receives the finished item."),
            ("Special Procurement: Consignment", "Vendor consignment allows vendor stock to be kept on company premises without incurring liability until consumed. Stock is held in consignment storage (movement type 411 K transfers consignment to own stock, triggering vendor liability)."),
            ("Purchasing Info Records and Source Lists", "Purchasing Info Records (ME11) link a specific vendor with a material, defining quotation prices, lead times, and tolerances. Source Lists (ME01) define preferred, allowable, or blocked sources of supply for given materials within plants."),
            ("Outline Agreements: Contracts and Scheduling", "Outline agreements include quantity/value contracts (ME31K) and scheduling agreements (ME31L). Scheduling agreements generate delivery schedules and forecast requirements directly for vendors, supporting JIT manufacturing."),
            ("Valuation Classes and Account Determination", "Valuation classes in the material master determine which general ledger accounts are updated during goods movements. Transaction OBYC configures automatic account determination using transaction keys like BSX (Inventory posting) and WRX (GR/IR clearing)."),
            ("Material Requirements Planning (MRP)", "MRP generates planned orders and purchase requisitions to satisfy dependent and independent demand. Net requirements calculations compare available warehouse stock and scheduled receipts against customer orders and planned production."),
            ("Split Valuation in SAP MM", "Split valuation allows a single material to be managed in inventory at different prices based on origin, batch, or quality. Valuation types are assigned to valuation areas, enabling accurate inventory balance sheet representation."),
            ("SAP MM Integration with Financial Accounting", "Every goods movement with financial impact automatically generates an FI document. Inventory accounts, consumption accounts, and price difference accounts (PRD) are posted real-time without batch reconciliations."),
            ("Troubleshooting and Common MM Errors", "Common MM issues include account determination errors (M8147), posting date blocked for period (M7053), and tolerance limit exceeded (M8082). Resolving these requires validating OBYC account keys, MMRV posting periods, and tolerance limits.")
        ]
    },
    {
        "filename": "SAP_FI_Financial_Accounting_Guide.pdf",
        "title": "SAP Financial Accounting (FI) Configuration and Operational Guide",
        "module": "SAP FI",
        "topics": [
            ("Introduction to SAP Financial Accounting", "SAP FI is the core module responsible for external reporting, balance sheets, profit and loss statements, and legal compliance. It records all financial transactions real-time and serves as the legal backbone of SAP ERP."),
            ("Company Code and Enterprise Structure", "Company Code is the smallest organizational unit for which a complete, self-contained set of accounts can be drawn up for legal reporting. It is identified by a 4-character alphanumeric code. Chart of Accounts is assigned to each company code."),
            ("General Ledger Accounting (FI-GL)", "General Ledger (FI-GL) provides a comprehensive record of all financial transactions. Every transaction posted in sub-ledgers (AR, AP, AA) updates the General Ledger real-time via reconciliation accounts. Master data is stored in tables SKA1 and SKB1."),
            ("Universal Journal Architecture (ACDOCA)", "In S/4HANA, the Universal Journal replaces traditional separate tables (BSIS, BSAS, BSIK, BSAK, COEP, FAGLFLEXA) with a single unified table: ACDOCA. ACDOCA holds both FI legal postings and CO managerial postings with up to 999,999 line items per document."),
            ("Chart of Accounts Architecture", "A Chart of Accounts contains definitions of all G/L accounts in a structured format. SAP supports Operational Chart of Accounts, Group Chart of Accounts (for corporate consolidation), and Country-Specific Chart of Accounts for local statutory reporting."),
            ("Fiscal Year Variants and Posting Periods", "Fiscal year variants define the relationship between the calendar year and posting periods. A standard fiscal year has 12 posting periods and up to 4 special periods for audit and year-end adjustments. Transaction OB52 controls open and closed posting periods."),
            ("Document Principles and Posting Keys", "Every financial posting in SAP produces an accounting document identified by Company Code, Document Number, and Fiscal Year. Posting keys (e.g. 01 for customer debit, 50 for G/L credit) control line item entry, debit/credit indicator, and field status."),
            ("Document Splitting in New G/L", "Document splitting automatically divides accounting lines across predetermined characteristics such as Segment or Profit Center during posting. This allows companies to create balanced financial statements for business segments and profit centers."),
            ("Accounts Payable (FI-AP) Operations", "Accounts Payable manages vendor financial accounting data. Invoices are posted via FB60 (direct FI invoice) or MIRO (logistics invoice). Payments are executed using the Automatic Payment Program (F110), generating bank payment media and clearing open items."),
            ("Accounts Receivable (FI-AR) Operations", "Accounts Receivable manages customer accounting transactions. Invoices originate from SD billing documents or direct FI entries (FB70). Incoming payments (F-28) clear open receivables, and the dunning program (F150) issues reminder notices for overdue balances."),
            ("Asset Accounting (FI-AA) Overview", "Asset Accounting manages fixed assets from capitalization to retirement. Asset classes group assets with similar depreciation terms and balance sheet accounts. Depreciation runs (AFAB) post planned depreciation to general ledger accounts monthly."),
            ("Bank Ledger and Electronic Bank Statement (EBS)", "Electronic Bank Statement (EBS) processes MT940 and CAMT.053 bank statement files. It automatically matches incoming receipts against open customer invoices and reconciles bank clearing accounts with the main cash ledger."),
            ("Withholding Tax and TDS Configuration", "Withholding tax configuration defines tax types, tax codes, and calculation bases for payments subject to tax deduction at source (TDS). SAP automatically deducts applicable withholding taxes during vendor invoice or payment processing."),
            ("Foreign Currency Valuation", "Foreign currency valuation (FAGL_FCV) revalues open foreign currency items and balance sheet accounts at period-end using closing exchange rates. Unrealized exchange gains or losses are posted automatically to designated P&L accounts."),
            ("Financial Closing Cockpit", "The Financial Closing Cockpit structures and automates the month-end and year-end financial close activities. It provides task lists, dependencies, automated batch execution, and audit-compliant progress monitoring across global entities."),
            ("Reconciliation Accounts and Sub-Ledgers", "Reconciliation accounts link sub-ledgers (customers, vendors, assets) to the General Ledger. Direct manual postings to reconciliation accounts are prohibited by system design to ensure absolute synchronization between sub-ledger and GL."),
            ("Validation and Substitution (GGB0 / GGB1)", "Validation rules check accounting document fields before posting to enforce business rules and data consistency. Substitution rules automatically replace or populate specific field values based on defined logical criteria."),
            ("Accrual Engine in SAP S/4HANA", "The S/4HANA Accrual Engine calculates and posts accruals and deferrals automatically. It integrates directly with purchase orders and contracts to eliminate manual recurring journal entries for deferred expenses."),
            ("Financial Reporting: Balance Sheet and P&L", "Financial Statement Versions (FSVs) group G/L accounts into hierarchical reporting structures representing Balance Sheet and Income Statement line items. FSVs are executed using transaction F.01 or Fiori analytical apps."),
            ("Common FI Configuration and Posting Issues", "Frequent FI issues include document imbalance errors (balance in transaction currency is not zero), closed posting period errors (M8053/F5201), and missing account assignment errors. Resolution requires adjusting OB52, FS00, or OBYC settings.")
        ]
    },
    {
        "filename": "SAP_CO_Controlling_Configuration_Handbook.pdf",
        "title": "SAP Controlling (CO) Managerial Accounting Handbook",
        "module": "SAP CO",
        "topics": [
            ("Controlling (CO) Fundamentals", "SAP Controlling provides information to company managers for decision making, internal planning, cost monitoring, and profitability analysis. Unlike FI, which is externally oriented, CO is strictly an internal management accounting system."),
            ("Controlling Area and Enterprise Structure", "The Controlling Area is the central organizational unit in CO. Multiple company codes can be assigned to a single controlling area provided they share the same operational chart of accounts and fiscal year variant, enabling cross-company controlling."),
            ("Cost Element Accounting", "Cost elements classify costs and revenues within the controlling area. In S/4HANA, cost elements are merged into G/L account master records (FS00) with account types: Primary Costs/Revenues, Secondary Costs, and Balance Sheet Accounts."),
            ("Cost Center Accounting (CO-OM-CCA)", "Cost Center Accounting monitors where costs occur within an organization. Cost centers represent organizational subunits such as departments. Master data is created via KS01 and organized into standard hierarchies (OKEON)."),
            ("Cost Center Planning and Budgeting", "Cost center planning sets cost targets for cost centers by activity types and cost elements. Budgets can be assigned to monitor actual spending against budgeted allocations using availability control mechanisms."),
            ("Internal Orders (CO-OM-OPA)", "Internal orders collect and control costs for specific temporary tasks, marketing campaigns, or investment projects. They can be statistical (for informational reporting) or real (requiring periodic settlement to cost centers, assets, or GLs)."),
            ("Activity Types and Rates", "Activity types represent services performed by cost centers (e.g. machine hours, labor hours). Plan and actual activity rates are calculated (KSPI) to allocate operational costs to production orders and internal cost collectors."),
            ("Cost Allocation: Assessments and Distributions", "Periodic cost allocations transfer costs from sender cost centers to receiver objects. Distribution uses the original primary cost element, while Assessment pools costs and transfers them using a secondary cost element (category 42)."),
            ("Profit Center Accounting (EC-PCA)", "Profit Center Accounting evaluates the operating profit of decentralized organizational subunits. Profit centers mirror operational business units or geographic divisions, generating internal income statements and balance sheets."),
            ("Product Cost Planning (CO-PC-PCP)", "Product Cost Planning calculates the cost of goods manufactured (COGM) and cost of goods sold (COGS) for products. It uses Bills of Materials (BOMs), Routings, and Costing Sheets to create standard cost estimates (CK11N/CK24)."),
            ("Cost Object Controlling (CO-PC-OBJ)", "Cost Object Controlling tracks actual costs incurred during the manufacturing process. It compares actual production costs (labor, materials, overhead) with target costs, calculating production variances (KSS2/KSS4/KKS2)."),
            ("WIP and Variance Calculation", "Work in Process (WIP) calculation determines the value of unfinished products at period-end (KKAX). Production variance calculation categorizes cost discrepancies into price variances, quantity variances, and scrap variances."),
            ("Profitability Analysis (CO-PA)", "Profitability Analysis evaluates the profitability of market segments (products, customers, sales organizations, distribution channels). Costing-based CO-PA uses value fields, while Margin Analysis in S/4HANA uses G/L accounts in ACDOCA."),
            ("Settlement Profiles and Allocation Rules", "Settlement profiles (OKO7) define the valid receivers (cost centers, fixed assets, G/L accounts) for internal orders and production orders. Allocation structures specify which cost elements settle to which accounts."),
            ("Costing Sheets and Overhead Calculation", "Costing sheets (KGI2) calculate and allocate overhead surcharges to production orders or projects based on base cost elements, percentage rates, and credits to overhead cost centers."),
            ("Statistical Key Figures (SKF)", "Statistical Key Figures represent measurable quantities (e.g. square footage, headcount, electricity kWh) used as tracing factors for accurate cost distribution and assessment cycles (KK01)."),
            ("Transfer Pricing in SAP CO", "Transfer pricing establishes internal clearing prices between corporate divisions to evaluate profit center margins under arm's length or group valuation viewpoints."),
            ("Material Ledger and Actual Costing", "The Material Ledger enables inventory valuation in multiple currencies and valuation methods. With Actual Costing, differences from standard costs are rolled into inventory and cost of goods sold at month-end."),
            ("Integration Between CO, PP, and SD", "CO integrates with PP via activity confirmation (CO11N) and order settlement, and with SD by posting billed revenues and sales deductions into profitability analysis upon billing document generation (VF01)."),
            ("Troubleshooting Controlling Variances", "Common CO errors involve missing cost element assignments (KI235), unassigned profit centers, and settlement errors (KD262). Troubleshooting requires verifying OKB9 default account assignments and settlement rules.")
        ]
    },
    {
        "filename": "SAP_SD_Sales_and_Distribution_Handbook.pdf",
        "title": "SAP Sales and Distribution (SD) Configuration and Logistics Guide",
        "module": "SAP SD",
        "topics": [
            ("SAP Sales and Distribution (SD) Overview", "SAP SD is the logistics module that manages the entire Order-to-Cash (O2C) business process, including pre-sales inquiries, quotations, sales order entry, delivery scheduling, warehouse picking, shipping, and customer invoicing."),
            ("SD Organizational Structure", "The SD enterprise structure comprises Sales Organization, Distribution Channel, and Division, which together form a Sales Area. Other elements include Sales Offices, Sales Groups, and Shipping Points."),
            ("Customer Master Data / Business Partner", "Customer master records maintain general data, company code accounting data, and sales area data. In S/4HANA, customers are created under Business Partner roles FLCU00 (FI Customer) and FLCU01 (Sales Customer)."),
            ("Customer-Material Info Record (VD51)", "Customer-Material Information Records store customer-specific material numbers, customer descriptions, and delivery tolerances. During sales order entry, the system automatically cross-references these records."),
            ("Sales Document Architecture", "Sales orders consist of three hierarchical tiers: Header (VBAK table, general customer data and terms), Item (VBAP table, material, quantity, and pricing), and Schedule Line (VBEP table, delivery dates and confirmed quantities)."),
            ("Sales Order Processing (VA01)", "Transaction VA01 is used to create sales documents such as standard orders (OR), rush orders, cash sales, and returns. The sales document type controls number ranges, partner determination, and delivery scheduling."),
            ("Pricing and Condition Technique", "The condition technique calculates prices, discounts, surcharges, and taxes in sales orders. Components include Condition Tables, Access Sequences, Condition Types (e.g. PR00 for base price, K004 for material discount), and Pricing Procedures."),
            ("Credit Management Integration (FSCM)", "Credit Management monitors customer credit exposure to mitigate financial default risk. When a customer exceeds their credit limit, sales orders are blocked (VKM3) until reviewed and released by credit analysts."),
            ("Availability Check (ATP) and Transfer of Requirements", "Available-to-Promise (ATP) checks ensure ordered goods can be supplied by the requested delivery date based on current warehouse stock, planned receipts, and confirmed customer orders. Advanced ATP (aATP) in S/4HANA provides product allocation and backorder processing."),
            ("Outbound Delivery Processing (VL01N)", "Outbound delivery documents are created via VL01N or collective processing (VL06O). Deliveries manage warehouse picking, packing into handling units, transportation planning, and Goods Issue."),
            ("Picking and Warehouse Management Integration", "Picking transfers goods from storage locations to shipping staging areas. The delivery integrates with Warehouse Management (WM) or Extended Warehouse Management (EWM) through transfer orders and warehouse tasks."),
            ("Post Goods Issue (PGI)", "Posting Goods Issue (movement type 601) transfers ownership of goods to the customer. PGI reduces inventory balance in MM and triggers an accounting document debiting Cost of Goods Sold (COGS) and crediting Inventory."),
            ("Billing and Invoicing (VF01)", "Transaction VF01 creates billing documents from outbound deliveries or sales orders. Billing documents record revenue, calculate sales taxes, and post real-time accounting entries debiting Customer Receivables and crediting Revenue accounts."),
            ("Partner Determination in SD", "Partner determination defines the business roles involved in sales transactions: Sold-to Party (orders goods), Ship-to Party (receives goods), Bill-to Party (receives invoice), and Payer (settles payment)."),
            ("Text and Output Determination", "Output determination controls the generation and transmission of order confirmations, delivery notes, and billing documents via print, email, or EDI/IDoc. Condition technique governs output trigger rules."),
            ("Returns and Credit Memos", "Customer returns are processed using return orders (RE), return deliveries (LR), and credit memos (CR). Returned materials are inspected (movement type 651/653) and credited to the customer account."),
            ("Consignment and Third-Party Sales", "In third-party processing, customer orders trigger automatic purchase requisitions to external vendors who ship directly to the end customer. Consignment fill-up, pick-up, and issue track stock kept at customer premises."),
            ("Intercompany Sales Processing", "Intercompany sales occur when a sales organization sells goods from a plant belonging to a different company code. SAP automatically generates an intercompany billing document (IV) between the internal entities."),
            ("Rebate and Settlement Management", "Condition contracts (WCOCO) in S/4HANA manage customer rebates and retrospective bonuses, replacing traditional ERP rebate agreements with unified Settlement Management."),
            ("Common SD Errors and Resolution", "Common SD issues include pricing errors (mandatory condition PR00 missing), delivery blocks due to credit limits, and billing creation blocks. Resolution entails reviewing pricing analysis (V/08) and credit logs.")
        ]
    },
    {
        "filename": "SAP_PP_Production_Planning_Reference.pdf",
        "title": "SAP Production Planning (PP) Reference and Shop Floor Guide",
        "module": "SAP PP",
        "topics": [
            ("SAP Production Planning (PP) Architecture", "SAP PP aligns manufacturing capabilities with customer demand. It covers demand management, sales and operations planning (S&OP), Material Requirements Planning (MRP), capacity planning, and shop floor order execution."),
            ("Bills of Material (BOM) - CS01", "A Bill of Materials (CS01) is a structured list of components, raw materials, and quantities needed to manufacture a product. BOMs can be single-level or multi-level, and are assigned to specific plants and usages."),
            ("Work Centers (CR01)", "Work centers represent production locations, machines, or labor groups where manufacturing activities take place. Key data includes available capacity, formulas for scheduling and costing, and cost center assignments."),
            ("Routings and Operations (CA01)", "A Routing (CA01) defines the sequence of manufacturing operations required to produce a material. Each operation specifies the work center, standard operational times (setup, machine, labor), and component allocations."),
            ("Demand Management and Planned Independent Requirements", "Planned Independent Requirements (PIRs, MD61) represent forecasted production quantities. Demand management strategies determine whether production is Make-to-Stock (MTS, strategy 10/40) or Make-to-Order (MTO, strategy 20/50)."),
            ("Material Requirements Planning (MRP Live)", "MRP compares requirements against warehouse inventory and planned receipts to generate planned orders and purchase requisitions. In S/4HANA, MRP Live runs in-memory directly on HANA, executing up to 10x faster than traditional ERP MRP."),
            ("Production Order Lifecycle", "The production order lifecycle encompasses: Order Creation (CO01), Order Release (CO02), Material Staging, Goods Issue of components (261), Operation Confirmation (CO11N), Goods Receipt of finished item (101), and Order Technical Completion (TECO)."),
            ("Material Staging and Goods Issue (MIGO / 261)", "Material staging brings raw materials from warehouse bins to the shop floor. Goods Issue with movement type 261 consumes components against the production order, updating actual material costs in the order cost collector."),
            ("Production Confirmation (CO11N)", "Production confirmation records completed operational quantities, scrap quantities, and actual machine/labor times. Confirmations update order status, reduce capacity requirements, and calculate activity costs."),
            ("Goods Receipt from Production (MIGO / 101)", "Completed finished products are received into inventory with movement type 101. This updates stock in warehouse storage locations and credits the production order at standard cost."),
            ("Capacity Requirements Planning (CRP)", "Capacity planning analyzes workload against available work center capacity over time buckets. Capacity leveling tools resolve overloads by adjusting operation start dates or shifting work to alternative machines."),
            ("Repetitive Manufacturing (PP-REM)", "Repetitive manufacturing is used for continuous, high-volume production lines. Production occurs against run schedules rather than discrete orders, and backflushing (MFBF) posts simultaneous component consumption and goods receipt."),
            ("Subcontracting in Production Orders", "External operations in routings subcontract specific manufacturing steps (e.g. heat treatment, painting) to outside vendors, generating subcontracting purchase requisitions automatically."),
            ("Scrap Management in Production", "Component scrap, assembly scrap, and operation scrap account for anticipated and actual manufacturing losses during production, ensuring MRP orders sufficient raw materials to yield required finished quantities."),
            ("Batch Management Integration", "Batch management assigns unique batch numbers to raw materials and finished products, enabling complete forward and backward traceability throughout the manufacturing supply chain."),
            ("Engineering Change Management (ECM)", "Engineering Change Management (CC01) manages modifications to BOMs, routings, and product designs with audit logging and effective date controls to maintain regulatory compliance."),
            ("Production Order Settlement and Variance", "Production orders are settled at month-end (KO88). The difference between actual costs debited and standard costs credited is posted to price difference accounts in general ledger accounting."),
            ("Shop Floor Control and Dispatching", "Shop floor control coordinates order sequencing and dispatching at individual work centers to minimize setup times and optimize machine utilization."),
            ("Integration with QM and PM", "PP integrates with Quality Management (QM) for in-process inspection lots (type 03) and with Plant Maintenance (PM) to schedule machine preventative maintenance without disrupting production."),
            ("Common PP Operational Errors", "Typical PP issues include missing component allocations in routings, scheduling errors due to missing work center formulas, and confirmation blocks. Resolutions involve checking CA02, CR02, and COFC error logs.")
        ]
    },
    {
        "filename": "SAP_HCM_Human_Capital_Management_Guide.pdf",
        "title": "SAP Human Capital Management (HCM) Administration Handbook",
        "module": "SAP HCM",
        "topics": [
            ("SAP HCM Architecture and Scope", "SAP HCM (Human Capital Management) oversees workforce administration, organizational structures, time evaluation, compensation, benefits, and payroll calculation across global enterprises."),
            ("Organizational Management (OM)", "Organizational Management defines organizational units, jobs, positions, and reporting hierarchies. Key object types include O (Org Unit), C (Job), S (Position), and P (Person), linked via relationships (e.g. S manages O)."),
            ("Personnel Administration (PA)", "Personnel Administration manages employee master data from hire to retire. Master data is structured in Infotypes (4-digit numerical codes). Transaction PA30 maintains infotype records, and PA20 displays employee data."),
            ("Key Infotypes in SAP HCM", "Essential infotypes include: 0000 (Actions), 0001 (Organizational Assignment), 0002 (Personal Data), 0006 (Addresses), 0007 (Planned Working Time), 0008 (Basic Pay), and 0009 (Bank Details)."),
            ("Personnel Actions (PA40)", "Personnel actions execute sequential infotype updates for employee lifecycle events such as Hiring, Promotion, Transfer, and Termination. Actions ensure mandatory employee records are completed consistently."),
            ("Time Management (PT)", "Time Management records and evaluates employee working hours, shifts, attendance, and absences (Infotypes 2001 and 2002). Time Evaluation (RPTIME00) calculates overtime, premiums, and quota deductions."),
            ("Leave Quotas and Absence Quotas (Infotype 2006)", "Absence quotas define employee entitlement to paid leave, sick leave, and vacation days. Quotas can be generated automatically via time evaluation rules or maintained manually."),
            ("Cross-Application Time Sheet (CATS)", "CATS allows employees and contractors to record project and operational hours across multiple modules (HCM, PS, PM, CO). Approved timesheet records transfer automatically to target modules."),
            ("Payroll Processing Overview", "The SAP Payroll driver (RPCALCx0) calculates gross and net pay, deductions, tax withholdings, and employer contributions. Payroll control records (PA03) safeguard data integrity during payroll execution."),
            ("Wage Types and Valuation", "Wage types classify monetary amounts and time units in payroll (e.g. base salary, bonus, overtime). Primary wage types are entered in master data (Infotype 0008/0014/0015); secondary wage types are generated during payroll runs."),
            ("Payroll Schema and Personnel Calculation Rules (PCR)", "Payroll schemas (e.g. US00 for USA, IN00 for India) structure payroll execution steps. Personnel Calculation Rules (PE02) process specific employee wage types conditionally."),
            ("Integration with Financial Accounting (FI)", "Completed payroll runs post to the General Ledger via posting program RPCIPE00. Salary expenses are debited to cost centers, and net pay liabilities and tax obligations are credited to vendor or clearing accounts."),
            ("SuccessFactors Integration Overview", "SAP HCM integrates with SAP SuccessFactors cloud modules (Employee Central, Performance & Goals, Learning, Succession) via SAP Cloud Integration Gateway for hybrid HR deployments."),
            ("Employee and Manager Self-Service (ESS/MSS)", "ESS and MSS Fiori apps enable employees to view payslips, submit leave requests, and update contact details, while managers approve time off and track team performance."),
            ("Benefits Administration", "Benefits administration manages health insurance, pension plans, and life insurance policies. Infotypes 0167, 0168, and 0169 record plan enrollments, employee contributions, and employer subsidies."),
            ("Compensation Management", "Compensation management models salary reviews, merit increases, and annual bonuses based on company budgets and individual employee performance appraisals."),
            ("Personnel Development and Qualifications", "Personnel development tracks employee competencies, licenses, and required qualifications against job and position profiles, highlighting training needs."),
            ("Standard HCM Reporting and Ad-Hoc Query", "The InfoSet Query and Ad-Hoc Query tools (S_PH0_48000513) allow HR analysts to build custom employee reports across multiple infotypes without programming."),
            ("Data Privacy and Authorization in HCM", "HCM data is subject to strict privacy regulations (GDPR). Contextual authorizations (P_ORGIN, P_PERNR) restrict HR access based on personnel area, employee subgroup, and organizational unit."),
            ("Common Payroll and Time Errors", "Common HCM issues include retroactive accounting date mismatches, missing basic pay infotypes, and unprocessed time pairs in time evaluation. Resolution involves checking PA03 and PT60 logs.")
        ]
    },
    {
        "filename": "SAP_S4HANA_Architecture_and_Migration_Guide.pdf",
        "title": "SAP S/4HANA Architecture and Migration Comprehensive Guide",
        "module": "SAP S/4HANA",
        "topics": [
            ("S/4HANA Platform Overview", "SAP S/4HANA is SAP's next-generation in-memory ERP suite designed for real-time analytics, instant transaction processing, and cloud deployment. It replaces the classic SAP ECC 6.0 architecture."),
            ("The HANA In-Memory Database Engine", "HANA stores data in RAM in columnar tables rather than row-based disk storage. This enables real-time aggregations on-the-fly, eliminating the need for aggregate tables and database indexes."),
            ("The Universal Journal (Table ACDOCA)", "ACDOCA consolidates General Ledger (FI), Controlling (CO), Asset Accounting (AA), Material Ledger (ML), and Profitability Analysis (CO-PA) into a single unified table with zero reconciliation overhead."),
            ("Business Partner (BP) Approach", "In S/4HANA, the Customer-Vendor Integration (CVI) framework mandates that all customers, vendors, and contacts be managed as Business Partners (transaction BP), retiring legacy transactions like XD01 and XK01."),
            ("Simplification List and Removed Functionality", "The SAP Simplification List documents changes, obsolete transactions, and merged functionalities between ECC and S/4HANA (e.g. MB01/MB1A replaced by MIGO; legacy credit management replaced by FSCM)."),
            ("Migration Paths: Greenfield, Brownfield, Selective", "Organizations migrate to S/4HANA via Greenfield (new implementation), Brownfield (system conversion preserving legacy data and customization), or Selective Data Transition (hybrid transition)."),
            ("Readiness Check and Maintenance Planner", "The SAP Readiness Check analyzes custom code compatibility, sizing requirements, financial data consistency, and active business functions prior to executing system conversion."),
            ("Software Update Manager (SUM) with DMO", "Database Migration Option (DMO) inside Software Update Manager combines database migration to HANA with the S/4HANA release upgrade into a single one-step downtime procedure."),
            ("Clean Core Strategy and Extensibility", "The Clean Core strategy keeps the ERP core unmodified, implementing customizations via SAP BTP using RAP, CAP, and In-App Key User Extensibility to allow seamless cloud upgrades."),
            ("Embedded Analytics and CDS Views", "S/4HANA provides operational analytics directly on transactional tables using ABAP Core Data Services (CDS) Views, removing the need to replicate data to an external data warehouse for operational reports."),
            ("Advanced ATP (aATP) in S/4HANA", "Advanced Available-to-Promise provides real-time multi-dimensional inventory checks, backorder processing (BOP) with win/gain/redistribute/fill/lose strategies, and product allocations."),
            ("Extended Warehouse Management (Embedded EWM)", "Embedded EWM in S/4HANA eliminates the need for a separate decentralized warehouse server, offering advanced wave management, slotting, and labor management within the core ERP."),
            ("Transportation Management (Embedded TM)", "Embedded TM plans, optimizes, and executes freight transportation directly within S/4HANA, coordinating freight orders, carrier selection, and freight settlement."),
            ("Central Finance (cFin) Architecture", "Central Finance replicates financial postings from multiple disparate ERP instances (SAP and non-SAP) real-time into a centralized S/4HANA system for consolidated financial reporting."),
            ("S/4HANA Cloud: Public vs Private Edition", "S/4HANA Public Cloud is a multi-tenant SaaS offering with bi-annual upgrades and standardized best practice processes. Private Cloud provides dedicated infrastructure and higher customization flexibility."),
            ("Fiori UX as Default S/4HANA Interface", "SAP Fiori is the standard user interface for S/4HANA, replacing SAP GUI with role-based, responsive web applications accessible across desktop and mobile devices."),
            ("Data Aging and Cold Store Management", "Data Aging moves historical transactional data from expensive memory to cold disk storage within the HANA database, optimizing RAM utilization and hardware footprint."),
            ("S/4HANA Security and Authorization", "S/4HANA security combines ABAP role authorizations (PFCG) with HANA database privilege controls, row-level SQL security, and Fiori catalog authorizations."),
            ("High Availability and Disaster Recovery (HSR)", "HANA System Replication (HSR) replicates data synchronously or asynchronously to secondary standby servers, ensuring minimal Recovery Time Objective (RTO) and Recovery Point Objective (RPO)."),
            ("Common S/4HANA Migration Obstacles", "Frequent migration issues involve un-synchronized CVI Business Partner records, custom ABAP code referencing obsolete aggregate tables (BSIS/GLT0), and inconsistent legacy asset accounting values.")
        ]
    },
    {
        "filename": "SAP_Fiori_Design_and_Deployment_Manual.pdf",
        "title": "SAP Fiori Design, Architecture and Deployment Manual",
        "module": "SAP Fiori",
        "topics": [
            ("Introduction to SAP Fiori", "SAP Fiori is the modern user experience (UX) paradigm for SAP software, delivering a consumer-grade, role-based, responsive, and coherent interface across devices."),
            ("Fiori Design Principles", "The five core Fiori principles are: Role-Based (tailored to user tasks), Responsive (adapts to device screen sizes), Simple (essential functions highlighted), Coherent (consistent design language), and Delightful."),
            ("Fiori App Types", "Fiori encompasses three primary application archetypes: Transactional Apps (task execution and approvals), Analytical Apps (real-time KPIs and visual charts), and Fact Sheets (contextual object 360-degree drill-down)."),
            ("SAP Fiori Launchpad (FLP)", "The Fiori Launchpad is the central web entry point for all Fiori apps. Users access role-specific tiles organized into Spaces, Pages, and Sections, with personalized bookmarks and notifications."),
            ("SAPUI5 Framework Architecture", "SAPUI5 is the enterprise-grade JavaScript UI framework powering Fiori apps. It implements Model-View-Controller (MVC) architecture, two-way data binding, responsive layout controls, and accessibility compliance."),
            ("OData Services and SAP Gateway", "Fiori apps communicate with backend SAP systems via RESTful OData (Open Data Protocol) services. SAP Gateway (/IWFND/GW_CLIENT) exposes ABAP business logic and CDS views as JSON/XML OData endpoints."),
            ("Fiori Elements and Smart Controls", "Fiori Elements generates standard UI layouts (List Report, Object Page, Analytical List Page, Overview Page) dynamically from backend CDS metadata annotations without writing frontend JavaScript."),
            ("Fiori Architecture: Embedded vs Hub Deployment", "In Embedded Deployment, Gateway and Fiori UI components reside directly on the backend S/4HANA system. Hub deployment placed Gateway on an independent frontend server, but Embedded is now SAP's recommended standard."),
            ("Spaces and Pages Concept in FLP", "Spaces and Pages replace legacy Classic Groups in the Fiori Launchpad. Spaces represent user roles (e.g. Accounts Payable Specialist), containing Pages that organize apps into intuitive functional sections."),
            ("Catalogs, Groups, and PFCG Roles", "Technical Catalogs store app definitions, while Business Catalogs assign apps to business roles. PFCG roles grant users authorization to specific catalogs, governing tile visibility on the launchpad."),
            ("Fiori Launchpad Configuration and Theming", "The UI Theme Designer allows enterprises to apply corporate branding, logos, color palettes, and typography to the Fiori Launchpad, supporting Horizon, Quartz Light, and Quartz Dark themes."),
            ("Custom Fiori App Development in SAP Business Application Studio", "Developers build custom Fiori applications in SAP Business Application Studio (BAS) using modern web tooling, TypeScript, ESLint, and Yeoman generators."),
            ("OData V2 vs OData V4", "OData V4 delivers improved performance, reduced payload sizes, batch request optimization, and enhanced query capabilities compared to OData V2, and is the default for new RAP services."),
            ("Fiori Notifications and Workflow Inbox", "The Fiori Launchpad Notification Center and My Inbox app aggregate workflow approval tasks (e.g. purchase orders, leave requests, travel expenses) for single-click approvals."),
            ("Fiori Search and Enterprise Search (ESH)", "Enterprise Search provides global keyword search across the entire SAP system directly from the Fiori Launchpad header bar, returning business objects with direct navigation links."),
            ("Offline Capabilities and Mobile Services", "SAP Mobile Services enables Fiori and native mobile apps to synchronize data securely for offline operation in field service and warehouse environments."),
            ("Cache Management and Cache Buster", "Fiori utilizes cache buster tokens to invalidate browser caches automatically when backend UI components or theme libraries are updated, preventing stale client scripts."),
            ("Troubleshooting Fiori Launchpad Issues", "Diagnostic tools include the Fiori Launchpad Content Manager (/UI2/FLC), Gateway error log (/IWFND/ERROR_LOG), and browser developer console for network and CORS errors."),
            ("Performance Optimization for Fiori", "Optimization techniques include enabling HTTP/2, compressing static resources with Gzip, activating app pre-loading, and using CDS paging to limit initial OData result payloads."),
            ("Security, Single Sign-On (SSO), and HTTPS", "Fiori deployments require HTTPS encryption and support SAML 2.0 and OpenID Connect (OIDC) for Single Sign-On across enterprise identity providers (e.g. Azure AD, Okta).")
        ]
    },
    {
        "filename": "SAP_ABAP_Development_and_RAP_Standards.pdf",
        "title": "SAP ABAP Modern Development and RAP Guidelines",
        "module": "SAP ABAP",
        "topics": [
            ("Evolution of the ABAP Programming Language", "ABAP has evolved from procedural report programming to Object-Oriented ABAP, and now to modern cloud-ready ABAP with strict typing, inline declarations, expressions, and clean core compliance."),
            ("Modern ABAP Syntax (7.40+)", "Modern ABAP features include inline data declarations (DATA(var) = ...), constructor operators (VALUE, COND, SWITCH), table expressions (it_tab[ key = val ]), and string templates (|Value: { var }|)."),
            ("Core Data Services (CDS) Views", "CDS Views define data models directly in the database layer. CDS supports associations, expressions, aggregations, input parameters, and UI annotations for automatic Fiori generation."),
            ("ABAP RESTful Application Programming Model (RAP)", "RAP is the modern standard architecture for developing cloud-ready applications and services on S/4HANA and SAP BTP. It replaces older BOPF and Gateway SEGW approaches."),
            ("RAP Architecture Layers", "RAP consists of: CDS Data Model layer, Behavior Definition (BDEF) specifying operations (Create, Update, Delete, Actions), Behavior Implementation (ABAP classes), and Service Definition / Service Binding."),
            ("Managed vs Unmanaged RAP Scenarios", "In Managed RAP, the framework automatically handles standard transactional operations (CRUD) and draft handling. In Unmanaged RAP, developers write custom save and locking logic for legacy APIs."),
            ("Draft Handling in RAP", "RAP draft handling allows business users to pause editing without losing changes, storing interim data in draft tables before committing the final transactional state to master database tables."),
            ("Business Add-Ins (BAdIs) and Enhancements", "The Enhancement Framework provides clean extension points. New BAdIs (SE18/SE19) allow custom business logic injection without modifying standard SAP code, supporting clean core upgradeability."),
            ("Classic APIs: BAPIs, RFCs, and IDocs", "BAPIs (Business Application Programming Interfaces) provide stable object-oriented RFC interfaces. IDocs (Intermediate Documents) enable asynchronous EDI communication between SAP and external systems."),
            ("SAP Gateway Service Development", "OData services are developed via RAP service bindings or transaction SEGW. Services define entity sets, navigations, and CRUDQ operations consumed by web applications and mobile devices."),
            ("Database Access: Open SQL and AMDP", "Modern Open SQL supports complex joins, CASE expressions, and string operations. ABAP Managed Database Procedures (AMDP) allow embedding native SQLScript directly in ABAP for high-performance computations."),
            ("Unit Testing with ABAP Unit", "ABAP Unit is the automated testing framework built into the ABAP workbench. Developers write automated unit test classes using test doubles and mocks for database tables and external services."),
            ("ABAP Test Cockpit (ATC) and Code Inspector", "ATC performs automated static code checks for syntax errors, performance bottlenecks, security flaws, and S/4HANA cloud readiness before transports can be released."),
            ("Object-Oriented Design Patterns in ABAP", "Best practices advocate standard design patterns including Factory, Singleton, Strategy, Observer, and Dependency Injection to ensure maintainability and testability in enterprise ABAP."),
            ("Exception Handling in Modern ABAP", "Class-based exceptions (CX_ROOT, CX_STATIC_CHECK) provide structured error handling with TRY...CATCH...CLEANUP blocks, replacing legacy return codes (SY-SUBRC)."),
            ("ABAP in Eclipse (ADT) Tooling", "ABAP Development Tools (ADT) in Eclipse provide a modern IDE with code completion, refactoring, quick fixes, interactive debugging, and CDS editors, superseding classic SE80."),
            ("Custom Code Migration to S/4HANA", "Custom code adaptation identifies non-compatible SQL constructs, obsolete table accesses (BSEG cluster), and non-standard sorting, adapting code for HANA database optimization."),
            ("ABAP Cloud and Developer Extensibility", "ABAP Cloud is the cloud-optimized development model for SAP S/4HANA Cloud and BTP. It restricts developers to released public APIs, preventing core ERP modifications."),
            ("Memory Management and LUWs in ABAP", "An SAP Logical Unit of Work (LUW) bundles database changes into an atomic transaction. Statements like CALL FUNCTION ... IN UPDATE TASK ensure changes commit reliably or roll back completely."),
            ("Troubleshooting ABAP Dumps (ST22)", "Short dumps occur on unhandled runtime exceptions. Transaction ST22 analyzes dump details, call stacks, active variable values, and error locations to diagnose system faults.")
        ]
    },
    {
        "filename": "SAP_Basis_Administration_and_Security_Handbook.pdf",
        "title": "SAP Basis Administration and System Security Handbook",
        "module": "SAP Basis",
        "topics": [
            ("SAP Basis and System Architecture", "SAP Basis is the foundational technology stack that provides the runtime environment for SAP applications. It connects the operating system, database, and ABAP/Java application servers."),
            ("SAP System Landscape (DEV, QAS, PRD)", "The standard enterprise landscape consists of three tiers: Development (DEV), Quality Assurance (QAS), and Production (PRD), ensuring software changes are thoroughly tested prior to live deployment."),
            ("Transport Management System (TMS / STMS)", "TMS coordinates the export and import of customization and development transport requests across the system landscape. Transaction STMS configures transport routes, domain controllers, and QA approval steps."),
            ("Work Process Monitoring (SM50 / SM66)", "SAP ABAP instances utilize dedicated work process types: Dialog (DIA), Background (BTC), Update (UPD/UPD2), Spool (SPO), and Enqueue (ENQ). SM50 displays local work processes, while SM66 monitors global cluster processes."),
            ("System Log and Dump Analysis (SM21 / ST22)", "SM21 provides real-time logging of critical system events, database errors, and security warnings. ST22 records detailed technical diagnosis for all runtime ABAP program cancellations (dumps)."),
            ("User Administration (SU01) and Identity Management", "Transaction SU01 creates and maintains user master records, specifying user types (Dialog, System, Communication, Service), validity periods, password policies, and assigned authorization roles."),
            ("Role Maintenance and Authorization (PFCG)", "Transaction PFCG designs authorization roles and profiles. Roles bundle authorization objects (e.g. S_TABU_DIS for table maintenance, S_TCODE for transaction access) according to the principle of least privilege."),
            ("Background Job Scheduling and Monitoring (SM36 / SM37)", "Background processing handles long-running tasks without tying up dialog work processes. SM36 schedules batch jobs with time or event triggers; SM37 monitors job execution logs and statuses."),
            ("Lock Management (SM12)", "The SAP Enqueue Server manages logical application locks to prevent concurrent modifications to the same business object. SM12 displays active locks and allows administrators to remove orphaned locks."),
            ("Performance Monitoring (ST03N / ST06)", "ST03N (Workload Monitor) analyzes transaction response times, database request times, and user activity profiles. ST06 monitors host operating system CPU, memory, and disk I/O metrics."),
            ("Database Administration and Backup Procedures", "HANA database administration involves monitoring memory usage, CPU allocation, savepoint performance, and scheduling regular data and log backups using SAP HANA Cockpit or DB13."),
            ("SAP System Upgrades and Support Package Stacks", "Support Package Stacks (SPS) apply software patches and legal updates. The Software Update Manager (SUM) executes automated system updates with minimal operational downtime."),
            ("Spool and Output Management (SP01 / SPAD)", "The SAP Spool system formats documents for printing or electronic export. SPAD configures output devices and print queues; SP01 tracks spool requests and print logs."),
            ("System Parameter Configuration (RZ10 / RZ11)", "Instance and default profile parameters control system behavior (e.g. login security policies, memory buffer sizes, work process counts). RZ10 maintains profiles on disk; RZ11 inspects dynamic parameters."),
            ("SAP Router and Remote Connectivity", "SAProuter is an application-level proxy that establishes secure, encrypted communication between customer SAP landscapes and SAP Support for remote maintenance and diagnostics."),
            ("Single Sign-On (SSO) and SNC Configuration", "Secure Network Communications (SNC) encrypts communications between SAP GUI and the application server. Enterprise SSO integrates Kerberos or SAML tokens to eliminate password prompts."),
            ("Audit Logging and Security Compliance (SM19 / SM20)", "The Security Audit Log (SM19 configuration, SM20 reporting) records sensitive system events including failed logins, user privilege changes, RFC executions, and critical transaction usage."),
            ("Client Administration and Copy (SCC4 / SCC9)", "A Client is an independent organizational and data entity within an SAP system. SCC4 sets client changeability options; SCC9 executes remote client copies between systems."),
            ("Disaster Recovery and High Availability Configuration", "High availability safeguards mission-critical systems through redundant application servers, Enqueue Replication Server (ERS), and database clustering to prevent single points of failure."),
            ("Common Basis Troubleshooting and Alerts", "Typical Basis issues include work process exhaustion (all DIA processes busy), lock table overflows, file system space shortages, and RFC connection failures (SM59).")
        ]
    }
]

def generate_pdf(manual_info: dict):
    filename = manual_info["filename"]
    filepath = DOCS_DIR / filename
    title = manual_info["title"]
    module = manual_info["module"]
    topics = manual_info["topics"]

    doc = pymupdf.open()

    for idx, (heading, body) in enumerate(topics):
        page_num = idx + 1
        page = doc.new_page(width=595, height=842) # A4 size

        # Header avoids implying official SAP authorship or confidentiality.
        header_text = f"Project-authored reference notes - {module.upper()}"
        page.insert_text(pymupdf.Point(50, 40), header_text, fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
        page.draw_line(pymupdf.Point(50, 46), pymupdf.Point(545, 46), color=(0.7, 0.7, 0.7), width=0.8)

        # Title / Topic Header
        page.insert_text(pymupdf.Point(50, 80), f"Section {page_num}: {heading}", fontsize=14, fontname="hebo", color=(0.08, 0.25, 0.55))
        page.insert_text(pymupdf.Point(50, 102), f"Module: {module} | Document: {filename}", fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))

        # Body Content
        full_text = (
            f"1.0 TECHNICAL SPECIFICATION AND ARCHITECTURE\n\n"
            f"{body}\n\n"
            f"2.0 OPERATIONAL AND CONFIGURATION DETAILS\n\n"
            f"In an enterprise production environment running {module}, this functionality is configured and maintained "
            f"according to SAP Best Practice methodologies. System administrators and functional consultants must ensure "
            f"that all prerequisites, master data records, and organizational assignments are established prior to execution.\n\n"
            f"Key transaction codes, database tables, and verification checkpoints associated with {heading} include:\n"
            f"- Primary Control Points: Ensure organizational authorization and period readiness.\n"
            f"- Data Integrity: Automated cross-table validation ensures zero orphaned records.\n"
            f"- Audit Compliance: System logs, change documents, and audit trails capture all transactional postings.\n\n"
            f"3.0 INTEGRATION TOUCHPOINTS\n\n"
            f"Seamless integration across logistics and finance is the hallmark of the SAP ERP ecosystem. Any transactional "
            f"event within {heading} updates general ledger postings, operational statuses, and downstream planning tools "
            f"in real-time, eliminating asynchronous reconciliation steps."
        )

        # Insert body text in a neat box
        rect = pymupdf.Rect(50, 125, 545, 780)
        page.insert_textbox(rect, full_text, fontsize=10.5, fontname="helv", lineheight=1.4, color=(0.1, 0.1, 0.1))

        # Footer
        page.draw_line(pymupdf.Point(50, 805), pymupdf.Point(545, 805), color=(0.7, 0.7, 0.7), width=0.8)
        footer_left = f"{title}"
        footer_right = f"Page {page_num} of {len(topics)}"
        page.insert_text(pymupdf.Point(50, 820), footer_left[:45], fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))
        page.insert_text(pymupdf.Point(490, 820), footer_right, fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(str(filepath))
    doc.close()
    print(f"Generated: {filename} ({len(topics)} pages)")

def main():
    print(f"Generating 10 realistic SAP reference manuals in: {DOCS_DIR}")
    for manual in MANUALS_SPEC:
        generate_pdf(manual)
    print("All 10 SAP PDF documents generated successfully!")

if __name__ == "__main__":
    main()
