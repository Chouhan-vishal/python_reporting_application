from users.services.utils import *


def sales_summary_query(start_date, end_date, pre_date, team_names= None):
    sub_query = ""
    if team_names:
        sub_query = f"WHERE ST.[Team Name] in ({team_names})"
    sql_query = f"""
        WITH SalesTeamCTE AS (
            SELECT   
                ST.[Team Name],   
                [Sales Person], 
                CAST(GETDATE() AS DATE) AS [Date],
                CAST(0 AS DECIMAL(10, 2)) AS [Target Qty],  
                CAST(0 AS DECIMAL(10, 2)) AS [Achv Qty],
                CAST(GETDATE() - 2 AS DATE) AS [Previous Date]
            FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
        ),
        TargetCustomers AS (
            SELECT DISTINCT  
                SV.[Team Name],    
                [Sales Person],
                ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10, 2))), 2) AS [Target Qty], 
                SV.[Date] 
            FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)
            WHERE [Item Category] <> 'Welding Electrodes'
            GROUP BY 
                SV.[Team Name],
                [Sales Person],
                SV.[Date]
        ),
        Sales AS (
            SELECT      
                ST.[Team Name],   
                [Sales Person],
                SUM([Qty(MTs)]) AS [Achv Qty], 
                ST.[Previous Date]
            FROM SalesTeamCTE ST
            INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
                ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
                AND SV.[Item Details] <> 'Welding Electrodes'
                AND SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY 
                ST.[Team Name],    
                [Sales Person],
                ST.[Previous Date]
        ),
        PreviousDateQty AS (
        SELECT
            ST.[Team Name],
            [Sales Person],
            SUM([Qty(MTs)]) AS [Achv Qty]
        FROM [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        WHERE SV.[Item Details] <> 'Welding Electrodes'
        AND CAST(SV.[Voucher Date] AS DATE) = '{pre_date}'
        GROUP BY ST.[Team Name], [Sales Person]
        )
        SELECT DISTINCT 
            ST.[Team Name],
            ST.[Sales Person],
            ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS [Target Qty],  
            ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS [Achv Qty],
            ISNULL(ROUND(CAST(ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT) / NULLIF(CAST(ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT), 0) * 100, 0), 0) AS [Achv %],
            ISNULL((SELECT [Achv Qty] FROM PreviousDateQty WHERE PreviousDateQty.[Team Name] = ST.[Team Name] AND PreviousDateQty.[Sales Person] = ST.[Sales Person]), 0) AS [Previous Date Qty]
        FROM SalesTeamCTE ST
        {sub_query}
        ORDER BY ST.[Team Name], ST.[Sales Person];
    """
    return sql_query


def sales_collection_outstanding_summary(pre_date, user, team_names=None):
    if is_salesman(user):
        full_name = user.full_name
        sub_query = f"""
        WHERE ST.[Team Name] IS NOT NULL
        AND (LOWER(ST.[Sales Person]) = LOWER('{full_name}') )"""
    elif is_manager(user):
        sub_query = f"WHERE ST.[Team Name] in ({team_names})"
    else:
        sub_query = 'WHERE ST.[Team Name] IS NOT NULL'
    sql_query = f"""
        WITH SalesTeam AS (
            SELECT DISTINCT  
                ST.[Team Name],   
                ST.[Sales Person]
            FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
        ),
        Sales AS (
            SELECT  
                ST.[Team Name],   
                ST.[Sales Person],
                SUM(SV.[Qty(MTs)]) AS Sales
            FROM SalesTeam ST
            INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
                ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
            WHERE 
                SV.[Voucher Date] = '{pre_date}'
                AND SV.[Item Details] <> 'Welding Electrodes'
            GROUP BY 
                ST.[Team Name],
                ST.[Sales Person]
        ),
        CollectionAmount AS (
            SELECT  
                ST.[Team Name],   
                ST.[Sales Person],
                SUM(RR.[Credit Amount]) AS [Collection Amount]
            FROM SalesTeam ST
            INNER JOIN [dbo].[tbl_ReceiptRegister] RR WITH (NOLOCK)
                ON LTRIM(RTRIM(RR.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
            WHERE 
                CAST(RR.[Receipt Date] AS DATE) = '{pre_date}'
            GROUP BY 
                ST.[Team Name],
                ST.[Sales Person]
        ),
        Outstandings AS (
            SELECT  
                ST.[Team Name],    
                ST.[Sales Person],
                SUM(OS.[Pending Amount]) AS [Total Outstanding],
                SUM(CASE WHEN OS.Ageing > 25 THEN OS.[Pending Amount] ELSE 0 END) AS [Above 25 Days Outstanding],
                SUM(CASE WHEN OS.Ageing > 45 THEN OS.[Pending Amount] ELSE 0 END) AS [Above 45 Days Outstanding],
                SUM(CASE WHEN OS.Ageing > 90 THEN OS.[Pending Amount] ELSE 0 END) AS [Above 90 Days Outstanding]
            FROM SalesTeam ST
            INNER JOIN [dbo].[tbl_OutStandings] OS WITH (NOLOCK)
                ON LTRIM(RTRIM(OS.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
            WHERE 
                CAST(OS.[Created Date] AS DATE) = (
                    SELECT MAX(CAST([Created Date] AS DATE)) 
                    FROM [dbo].[tbl_OutStandings] OS2 WITH (NOLOCK)
                )
            GROUP BY 
                ST.[Team Name],
                ST.[Sales Person]
        ),
        PreDaySales AS (
            SELECT
                ST.[Team Name],
                ST.[Sales Person],
                SUM(SV.[Qty(MTs)]) AS [PreDaySales]
            FROM SalesTeam ST
            INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
                ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
            WHERE 
                CAST(SV.[Voucher Date] AS DATE) = '{pre_date}'
                AND SV.[Item Details] <> 'Welding Electrodes'
            GROUP BY
                ST.[Team Name],
                ST.[Sales Person]
        )
        SELECT DISTINCT 
            ST.[Team Name],
            ST.[Sales Person],
            COALESCE(S.Sales, 0) AS Sales,
            COALESCE(CA.[Collection Amount], 0) AS [Collection Amount],
            COALESCE(O.[Total Outstanding], 0) AS [Total Outstanding],
            COALESCE(O.[Above 25 Days Outstanding], 0) AS [Above 25 Days Outstanding],
            COALESCE(O.[Above 45 Days Outstanding], 0) AS [Above 45 Days Outstanding],
            COALESCE(O.[Above 90 Days Outstanding], 0) AS [Above 90 Days Outstanding],
            COALESCE(PDS.[PreDaySales], 0) AS [PreDaySales]
        FROM SalesTeam ST
        LEFT JOIN Sales S
            ON ST.[Team Name] = S.[Team Name] AND ST.[Sales Person] = S.[Sales Person]
        LEFT JOIN CollectionAmount CA
            ON ST.[Team Name] = CA.[Team Name] AND ST.[Sales Person] = CA.[Sales Person]
        LEFT JOIN Outstandings O
            ON ST.[Team Name] = O.[Team Name] AND ST.[Sales Person] = O.[Sales Person]
        LEFT JOIN PreDaySales PDS
            ON ST.[Team Name] = PDS.[Team Name] AND ST.[Sales Person] = PDS.[Sales Person]
        {sub_query}
        ORDER BY ST.[Team Name], ST.[Sales Person];
    """
    return sql_query


def product_wise_sales_summary_query(start_date, end_date, pre_date, team_names = None):
    sub_query = ""
    if team_names:
        sub_query = f"[Team Name] IN ({team_names})"
    sql_query = f"""
    WITH TargetCustomers AS (
    SELECT
        [Item Category],
        ROUND(SUM(CAST([Target Qty] AS Decimal(10,2))), 2) AS [Target Qty]
    FROM [dbo].[tbl_TargetCustomers] WITH (NOLOCK)   
    WHERE [Item Category] <> 'Welding Electrodes'
        AND {sub_query}
    GROUP BY [Item Category]
    ),
    Sales AS (
    SELECT          
        IL.[Item Category] as [Item Category],
        CAST(0 AS Decimal(10,2)) AS [Target Qty],
        ISNULL(SUM(CASE WHEN SV.[Item Details] <> 'Welding Electrodes' THEN [Qty(MTs)] ELSE 0 END), 0) AS [Achv Qty] 
    FROM (SELECT DISTINCT
            [Item Details],
            [Item Category] 
            FROM dbo.tbl_ItemsList IL  WITH(Nolock)) IL   
    INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(Nolock) 
        ON IL.[Item Details] = SV.[Item Details]  
    WHERE SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'  
        AND SV.[Item Details] <> 'Welding Electrodes' 
        AND SV.[Sales Person -1] IN (SELECT [Sales Person] 
                                    FROM [dbo].[tbl_SalesTeam] 
                                    WHERE {sub_query})  -- Adding the Team Name filter
    GROUP BY IL.[Item Category]
    ),
    PreviousDateQty AS (
    SELECT          
        IL.[Item Category] as [Item Category],
        CAST(0 AS Decimal(10,2)) AS [Target Qty],
        ISNULL(SUM(CASE WHEN SV.[Item Details] <> 'Welding Electrodes' THEN [Qty(MTs)] ELSE 0 END), 0) AS [Achv Qty] 
    FROM (SELECT DISTINCT
            [Item Details],
            [Item Category] 
            FROM dbo.tbl_ItemsList IL  WITH(Nolock)) IL   
    INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(Nolock) 
        ON IL.[Item Details] = SV.[Item Details]  
    WHERE 
        CAST(SV.[Voucher Date] AS DATE) = '{pre_date}'
        AND SV.[Item Details] <> 'Welding Electrodes' 
        AND SV.[Sales Person -1] IN (SELECT [Sales Person] 
                                    FROM [dbo].[tbl_SalesTeam] 
                                    WHERE {sub_query})  -- Adding the Team Name filter
    GROUP BY IL.[Item Category]
    )
    SELECT 
    TC.[Item Category] AS [item_category],
    TC.[Target Qty] AS [target_qty],
    ISNULL(S.[Achv Qty], 0) AS [achvd_qty],
    ISNULL(PDQ.[Achv Qty], 0) AS [pre_day_sales],
    CASE 
        WHEN TC.[Target Qty] = 0 THEN 0
        ELSE (ISNULL(S.[Achv Qty], 0) / TC.[Target Qty]) * 100 
    END AS [achievement_percentage]
    FROM TargetCustomers TC
    LEFT JOIN Sales S ON TC.[Item Category] = S.[Item Category]
    LEFT JOIN PreviousDateQty PDQ ON TC.[Item Category] = PDQ.[Item Category]
    ORDER BY TC.[Item Category];

    """
    return sql_query

def weekly_report_query(user, team_names):

    if is_salesman(user):
        full_name = user.full_name
        sub_query = f"""
        WHERE ST.[Team Name] IS NOT NULL
        AND (LOWER(ST.[Sales Person]) = LOWER('{full_name}'))"""
    elif is_manager(user):
        sub_query = f"WHERE ST.[Team Name] in ({team_names})"
    else:
        sub_query = ''

    sql_query = f"""
    DECLARE @WeekStartDayMonday DATE, @WeekEndDaySaturday DATE;

    SELECT  
        @WeekStartDayMonday = CAST(DATEADD(wk, DATEDIFF(wk, 0, GETDATE()), 0) AS DATE),   
        @WeekEndDaySaturday = CAST(DATEADD(WEEK, 1, DATEADD(DAY, -1 * DATEPART(weekday, GETDATE()), GETDATE())) AS DATE);

    -- Working days count in the current month
    DECLARE @Workingdays INT;
    SELECT @Workingdays = COUNT([CalendarDate])
    FROM [dbo].[tbl_Calendar] WITH (NOLOCK)
    WHERE [HolidayFlag] <> 'Y' 
        AND YEAR([CalendarDate]) = YEAR(GETDATE())
        AND MONTH([CalendarDate]) = MONTH(GETDATE())
        AND CAST([CalendarDate] AS DATE) > CAST(GETDATE() AS DATE);

    -- CTEs for various calculations
    WITH SalesTeam AS (
        SELECT DISTINCT
            ST.[Team Name],   
            [Sales Person],
            CAST(0 AS DECIMAL(12,2)) AS [Target Qty],
            CAST(0 AS DECIMAL(12,2)) AS [Achv Qty],
            CAST(0 AS DECIMAL(12,2)) AS [Collection Target],
            CAST(0 AS DECIMAL(12,2)) AS [Collection Achv],
            CAST(0 AS DECIMAL(12,2)) AS [Pending Target],
            CAST(0 AS DECIMAL(12,2)) AS [Daily Target]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
    ),
    TargetCustomers AS (
        SELECT 
            SV.[Team Name],  
            SV.[Sales Person], 
            ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10,2))), 2) AS [Target Qty]
        FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)  
        WHERE [Item Category] <> 'Welding Electrodes'
        GROUP BY SV.[Team Name], SV.[Sales Person]
    ),
    Sales AS (
        SELECT
            ST.[Team Name],   
            ST.[Sales Person],
            SUM([Qty(MTs)]) AS [Achv Qty]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK) 
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK) 
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person])) 
        WHERE YEAR(SV.[Voucher Date]) = YEAR(GETDATE()) 
            AND MONTH(SV.[Voucher Date]) = MONTH(GETDATE()) 
            AND SV.[Item Details] <> 'Welding Electrodes'
        GROUP BY ST.[Team Name], ST.[Sales Person]
    ),
    WeeklySales AS (
        SELECT
            ST.[Team Name],   
            ST.[Sales Person],
            SUM([Qty(MTs)]) AS [Weekly Achvd Qty]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK) 
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK) 
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person])) 
        WHERE YEAR(SV.[Voucher Date]) = YEAR(GETDATE()) 
            AND MONTH(SV.[Voucher Date]) = MONTH(GETDATE()) 
            AND SV.[Item Details] <> 'Welding Electrodes'
            AND CAST(SV.[Voucher Date] AS DATE) BETWEEN @WeekStartDayMonday AND @WeekEndDaySaturday
        GROUP BY ST.[Team Name], ST.[Sales Person]
    ),
    CollectionAmount AS (
        SELECT
            ST.[Team Name],  
            ST.[Sales Person],
            SUM(RR.[Credit Amount]) AS [Collection Amount]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)  
        INNER JOIN [dbo].[tbl_ReceiptRegister] RR WITH (NOLOCK) 
            ON LTRIM(RTRIM(RR.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))  
        WHERE CAST(RR.[Receipt Date] AS DATE) BETWEEN @WeekStartDayMonday AND @WeekEndDaySaturday
        GROUP BY ST.[Team Name], ST.[Sales Person]
    ),
    Outstandings AS (
        SELECT
            ST.[Sales Person],
            SUM(OS.[Pending Amount]) AS [Total Outstanding],
            SUM(CASE WHEN OS.Ageing > 25 THEN OS.[Pending Amount] END) AS [Above 25 Days Outstanding]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)  
        INNER JOIN [dbo].[tbl_OutStandings] OS WITH (NOLOCK) 
            ON LTRIM(RTRIM(OS.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))  
        WHERE CAST(OS.[Created Date] AS DATE) = (
            SELECT MAX(CAST([Created Date] AS DATE))
            FROM [dbo].[tbl_OutStandings] OS WITH (NOLOCK)
        )
        GROUP BY ST.[Sales Person]
    )
    SELECT DISTINCT 
        CAST(GETDATE() AS DATE) AS [Sales Date],
        DATENAME(MONTH, GETDATE()) AS [Month],
        YEAR(GETDATE()) AS [Year],
        ST.[Team Name] AS [Team],
        ST.[Sales Person] AS [Sales Men], 
        COALESCE(TC.[Target Qty], 0) AS [Sales Target],
        COALESCE(S.[Achv Qty], 0) AS [Achv],
        ISNULL(ROUND(CAST(COALESCE(S.[Achv Qty], 0) AS FLOAT) / NULLIF(CAST(COALESCE(TC.[Target Qty], 0) AS FLOAT), 0) * 100, 0), 0) AS [Achv %],
        CAST(COALESCE(TC.[Target Qty], 0) - COALESCE(S.[Achv Qty], 0) AS DECIMAL(12,2)) AS [Pending Target],
        CAST((COALESCE(TC.[Target Qty], 0) - COALESCE(S.[Achv Qty], 0)) / @Workingdays AS DECIMAL(12,2)) AS [Daily Target],
        CAST(((COALESCE(TC.[Target Qty], 0) - COALESCE(S.[Achv Qty], 0)) / @Workingdays) * 6 AS DECIMAL(12,2)) AS [Weekly Target],
        COALESCE(O.[Above 25 Days Outstanding], 0) AS [Collection Target],
        COALESCE(CA.[Collection Amount], 0) AS [Collection Achv],
        COALESCE(WS.[Weekly Achvd Qty], 0) AS [Weekly Achvd Qty]
    FROM SalesTeam ST
    LEFT JOIN TargetCustomers TC ON ST.[Sales Person] = TC.[Sales Person]
    LEFT JOIN Sales S ON ST.[Sales Person] = S.[Sales Person] AND ST.[Team Name] = S.[Team Name]
    LEFT JOIN CollectionAmount CA ON ST.[Sales Person] = CA.[Sales Person]
    LEFT JOIN Outstandings O ON ST.[Sales Person] = O.[Sales Person]
    LEFT JOIN WeeklySales WS ON ST.[Sales Person] = WS.[Sales Person] AND ST.[Team Name] = WS.[Team Name]

    {sub_query}
    ORDER BY ST.[Team Name] ;

        """
    return sql_query

def collection_report_by_date_range(date, user, team_names):

    if is_salesman(user):
        full_name = user.full_name
        sub_query = f"AND LOWER(ST.[Sales Person]) = LOWER('{full_name}')"
    elif is_manager(user):
        sub_query = f"AND ST.[Team Name] in ({team_names})"
    else:
        sub_query = ''

    # Define the SQL query
    sql_query = f"""
        SELECT st.[Team Name],
            st.[Sales Person],
            SUM(rr.[Credit Amount]) AS TotalCreditAmount
        FROM tbl_SalesTeam st
        JOIN tbl_ReceiptRegister rr ON st.[Sales Person] = rr.[Sales Person -2]
        WHERE rr.[Receipt Date] = '{date}'
        {sub_query}
        GROUP BY st.[Team Name],
                st.[Sales Person]
        ORDER BY 1;
    """
    return sql_query


def customer_wise_outstanding_query(outstanding_value, user, team_names, salesman=None):
    if is_salesman(user):
        full_name = user.full_name
        sub_query = f"AND (LOWER(ST.[Sales Person]) = LOWER('{full_name}'))"
    elif is_manager(user):
        sub_query = f"AND ST.[Team Name] in ({team_names})"
        if salesman:
            sub_query += f"AND (LOWER(ST.[Sales Person]) = LOWER('{salesman}'))"
    else:
        sub_query = ''

    sql_query = f"""
        SELECT  
            OS.[Branch Name],
            OS.[Bill NO],
            OS.[Customer Name],
            OS.Ageing,
            SUM(CASE WHEN OS.Ageing > {outstanding_value} THEN OS.[Pending Amount] ELSE 0 END) AS [Above {outstanding_value} Days Outstanding]
        FROM [dbo].[tbl_OutStandings] OS
        INNER JOIN [dbo].[tbl_SalesTeam] ST 
            ON LTRIM(RTRIM(OS.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        WHERE 
            CAST(OS.[Created Date] AS DATE) = (
                SELECT MAX(CAST([Created Date] AS DATE)) 
                FROM [dbo].[tbl_OutStandings] OS2
            )
        {sub_query}
        GROUP BY 
            OS.[Branch Name],
            OS.[Bill NO],
            OS.[Customer Name],
            OS.Ageing
        HAVING 
            SUM(CASE WHEN OS.Ageing > {outstanding_value} THEN OS.[Pending Amount] ELSE 0 END) > 0
        ORDER BY OS.[Branch Name],
        OS.[Bill NO], 
        OS.[Customer Name], 
        OS.Ageing;
        """
    return sql_query



def cr_utilization_report_query(user, team_names, salesman = None):
    if is_salesman(user):
        full_name = user.full_name
        sub_query = f"AND (LOWER(t1.[Sales Person]) = LOWER('{full_name}'))"
    elif is_manager(user):
        sub_query = f"AND t1.[Team Name] in ({team_names})"
        if salesman:
            sub_query += f"AND (LOWER(t1.[Sales Person]) = LOWER('{salesman}'))"
    else:
        sub_query = ''
    sql_query = f"""
        SELECT 
            t1."Team Name", 
            t1."Sales Person", 
            t1."Customer Name", 
            t1."Customer ID", 
            SUM(CONVERT(FLOAT, t1."Target Qty")) AS "Total Target Qty", 
            SUM(CONVERT(FLOAT, t1."Target Qty") * 92000) AS "CR Limit",
            ISNULL(SUM_OUTSTANDING.[All Outstanding], 0) AS "All Outstanding",
            CASE 
                WHEN SUM(CONVERT(FLOAT, t1."Target Qty") * 92000) = 0 THEN 0  -- Handle division by zero
                ELSE (CAST(ISNULL(SUM_OUTSTANDING.[All Outstanding], 0) AS FLOAT) / (SUM(CONVERT(FLOAT, t1."Target Qty") * 92000)) * 100) 
            END AS "CR %"
        FROM 
            tbl_TargetCustomers t1
        LEFT JOIN 
            (
            SELECT 
                OS.[Customer Name], 
                SUM(CASE WHEN OS.Ageing > 0 THEN OS.[Pending Amount] ELSE 0 END) AS [All Outstanding]
            FROM 
                [dbo].[tbl_OutStandings] OS
            INNER JOIN 
                [dbo].[tbl_SalesTeam] ST ON LTRIM(RTRIM(OS.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
            WHERE 
                CAST(OS.[Created Date] AS DATE) = (SELECT MAX(CAST([Created Date] AS DATE)) FROM [dbo].[tbl_OutStandings] OS2)
            GROUP BY 
                OS.[Customer Name]
            HAVING 
                SUM(CASE WHEN OS.Ageing > 0 THEN OS.[Pending Amount] ELSE 0 END) > 0
            ) AS SUM_OUTSTANDING ON t1."Customer Name" = SUM_OUTSTANDING.[Customer Name]
        WHERE 
            t1."Item Category" <> 'Welding Electrodes'
            {sub_query}
        GROUP BY 
            t1."Team Name", t1."Sales Person", t1."Customer Name", t1."Customer ID", SUM_OUTSTANDING.[All Outstanding] -- Include "All Outstanding" in the GROUP BY clause
        ORDER BY 
            t1."Team Name", t1."Sales Person", t1."Customer Name", t1."Customer ID";

            """
    return sql_query


def team_and_product_wise_query(start_date, end_date, pre_date):
    sql_query = f"""
    WITH SalesTeamCTE AS (
        SELECT   
            ST.[Team Name],   
            [Sales Person], 
            CAST(GETDATE() AS DATE) AS [Date],
            CAST(0 AS DECIMAL(10, 2)) AS [Target Qty],  
            CAST(0 AS DECIMAL(10, 2)) AS [Achv Qty],
            CAST(GETDATE() - 2 AS DATE) AS [Previous Date]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
    ),
    TargetCustomers AS (
        SELECT DISTINCT  
            SV.[Team Name],    
            [Sales Person],
            ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10, 2))), 2) AS [Target Qty], 
            SV.[Date] 
        FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)
        WHERE [Item Category] <> 'Welding Electrodes'
        GROUP BY 
            SV.[Team Name],
            [Sales Person],
            SV.[Date]
    ),
    Sales AS (
        SELECT      
            ST.[Team Name],   
            [Sales Person],
            SUM([Qty(MTs)]) AS [Achv Qty], 
            ST.[Previous Date]
        FROM SalesTeamCTE ST
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
            AND SV.[Item Details] <> 'Welding Electrodes'
            AND SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY 
            ST.[Team Name],    
            [Sales Person],
            ST.[Previous Date]
    ),
    PreviousDateQty AS (
    SELECT
        ST.[Team Name],
        [Sales Person],
        SUM([Qty(MTs)]) AS [Achv Qty]
    FROM [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
    INNER JOIN [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
        ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
    WHERE SV.[Item Details] <> 'Welding Electrodes'
    AND CAST(SV.[Voucher Date] AS DATE) = '{pre_date}'
    GROUP BY ST.[Team Name], [Sales Person]
    )
    SELECT DISTINCT 
        ST.[Team Name],
        ST.[Sales Person],
        ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS [Target Qty],  
        ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS [Achv Qty],
        ISNULL(ROUND(CAST(ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT) / NULLIF(CAST(ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT), 0) * 100, 0), 0) AS [Achv %],
        ISNULL((SELECT [Achv Qty] FROM PreviousDateQty WHERE PreviousDateQty.[Team Name] = ST.[Team Name] AND PreviousDateQty.[Sales Person] = ST.[Sales Person]), 0) AS [Previous Date Qty]
    FROM SalesTeamCTE ST
    ORDER BY ST.[Team Name], ST.[Sales Person];
    """
    return sql_query


def salesman_and_product_wise_query(user, team_names, month, year, salesman=None):
    if is_salesman(user):
        achv_qty_clause=''
        target_filter_clause=''
        voucher_filter_clause=''
        full_name = user.full_name
        # Calculation for Achv Qty specific to salesmen
        achv_qty_clause = """
            SUM(CASE
                WHEN SV.[Item Details] = 'Welding Electrodes' THEN [Qty(Box)]
                ELSE [Qty(MTs)]
            END) AS [Achv Qty]
        """
        target_filter_clause = ""
        voucher_filter_clause = ""
        sub_query = f"AND (LOWER(ST.[Sales Person]) = LOWER('{full_name}'))"
    elif is_manager(user):
        achv_qty_clause = """
            SUM(CASE
                WHEN SV.[Item Details] <> 'Welding Electrodes' THEN [Qty(MTs)]
                ELSE 0
            END) AS [Achv Qty]
        """
        target_filter_clause = "WHERE [Item Category] <> 'Welding Electrodes'"
        voucher_filter_clause = " AND SV.[Item Details] <> 'Welding Electrodes' "
        sub_query = f"AND ST.[Team Name] in ({team_names})"
        if salesman:
            sub_query += f"AND (LOWER(ST.[Sales Person]) = LOWER('{salesman}'))"
    else:
        sub_query = ''

    sql_query = f"""
    WITH Sales AS (
        SELECT
            ST.[Sales Person],
            IL.[Item Category] AS [Product cluster],
            ISNULL(TC.[Target Qty], 0) AS [Target Qty],
            {achv_qty_clause}
        FROM [dbo].[tbl_SalesTeam] ST WITH(NOLOCK)
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(NOLOCK)
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        INNER JOIN (
            SELECT DISTINCT
                [Item Details],
                [Item Category]
            FROM dbo.tbl_ItemsList IL WITH(NOLOCK)
        ) IL
            ON IL.[Item Details] = SV.[Item Details]
        LEFT JOIN (
            SELECT
                [Sales Person],
                [Item Category] AS [Product cluster],
                ROUND(SUM(CAST([Target Qty] AS DECIMAL(10,2))),2) AS [Target Qty]
            FROM [dbo].[tbl_TargetCustomers] WITH(NOLOCK)
            {target_filter_clause}
            GROUP BY
                [Sales Person],
                [Item Category]
        ) TC
            ON TC.[Sales Person] = ST.[Sales Person] AND TC.[Product cluster] = IL.[Item Category]
        WHERE YEAR(SV.[Voucher Date]) = {year} AND MONTH(SV.[Voucher Date]) = {month}  {voucher_filter_clause}
        {sub_query}
        GROUP BY
            ST.[Sales Person],
            IL.[Item Category],
            TC.[Target Qty]
    )
    SELECT    
        [Sales Person],
        [Product cluster],
        [Target Qty],
        SUM([Achv Qty]) AS [Achv Qty],
        ISNULL(ROUND(SUM([Achv Qty]) / NULLIF([Target Qty], 0) * 100, 0), 0) AS [Achv %]
    FROM Sales
    GROUP BY
        [Sales Person],
        [Product cluster],
        [Target Qty];
     """
    return sql_query

def target_and_achieved_query(year, month, pre_day, user, team_names):

    if is_salesman(user):
        full_name = user.full_name
        sub_query = f"WHERE (LOWER(ST.[Sales Person]) = LOWER('{full_name}'))"
    elif is_manager(user):
        sub_query = f"WHERE ST.[Team Name] in ({team_names})"
    else:
        sub_query = ''

    sql_query = f"""
    WITH SalesTeamCTE AS (
        SELECT   
            ST.[Team Name],   
            [Sales Person], 
            CAST(GETDATE() AS DATE) AS [Date],
            CAST(0 AS DECIMAL(10, 2)) AS [Target Qty],  
            CAST(0 AS DECIMAL(10, 2)) AS [Achv Qty],
            CAST(GETDATE() - 2 AS DATE) AS [Previous Date]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
    ),
    TargetCustomers AS (
        SELECT DISTINCT  
            SV.[Team Name],    
            [Sales Person],
            ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10, 2))), 2) AS [Target Qty], 
            SV.[Date],
            COUNT(DISTINCT SV.[Customer ID]) AS [Target Customer Count]
        FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)
        WHERE [Item Category] <> 'Welding Electrodes'
        GROUP BY 
            SV.[Team Name],
            [Sales Person],
            SV.[Date]
    ),
    Sales AS (
        SELECT      
            ST.[Team Name],   
            [Sales Person],
            SUM([Qty(MTs)]) AS [Achv Qty], 
            ST.[Previous Date]
        FROM SalesTeamCTE ST
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
            AND SV.[Item Details] <> 'Welding Electrodes'
            AND YEAR(SV.[Voucher Date]) = {year} AND MONTH(SV.[Voucher Date]) = {month} 
        GROUP BY 
            ST.[Team Name],    
            [Sales Person],
            ST.[Previous Date]
    ),
    CustomerReached AS (
        SELECT      
            TC.[Team Name],
            TC.[Sales Person],
            COUNT(DISTINCT CASE WHEN [Qty(MTs)] > 0 THEN SV.[Customer ID] ELSE NULL END) AS [Target Customer Reached]
        FROM [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_TargetCustomers] TC WITH (NOLOCK)
            ON SV.[Customer ID] = TC.[Customer ID]
        WHERE SV.[Item Details] <> 'Welding Electrodes'
        AND YEAR(SV.[Voucher Date]) = {year} AND MONTH(SV.[Voucher Date]) = {month}
        GROUP BY 
            TC.[Team Name], TC.[Sales Person]
    ),
    PreviousDateQty AS (
        SELECT
            ST.[Team Name],
            [Sales Person],
            SUM([Qty(MTs)]) AS [Achv Qty]
        FROM [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        WHERE SV.[Item Details] <> 'Welding Electrodes'
        AND CAST(SV.[Voucher Date] AS DATE) = '{pre_day}'
        GROUP BY ST.[Team Name], [Sales Person]
    ),
    Outstanding AS (
        SELECT  
            ST.[Team Name],
            OS.[Sales Person -2] AS [Sales Person],
            SUM(CASE WHEN OS.Ageing > 25 THEN OS.[Pending Amount] ELSE 0 END) AS [Above 25 Days Outstanding]
        FROM [dbo].[tbl_OutStandings] OS WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
            ON LTRIM(RTRIM(OS.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        WHERE 
            CAST(OS.[Created Date] AS DATE) = (
                SELECT MAX(CAST([Created Date] AS DATE)) 
                FROM [dbo].[tbl_OutStandings] OS2
            )
        GROUP BY 
            ST.[Team Name],
            OS.[Sales Person -2]
    )
    SELECT DISTINCT 
        ST.[Team Name],
        ST.[Sales Person],
        ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS [Target Qty],  
        ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS [Achv Qty],
        ISNULL(ROUND(CAST(ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT) / NULLIF(CAST(ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT), 0) * 100, 0), 0) AS [Achv %],
        ISNULL((SELECT [Achv Qty] FROM PreviousDateQty WHERE PreviousDateQty.[Team Name] = ST.[Team Name] AND PreviousDateQty.[Sales Person] = ST.[Sales Person]), 0) AS [Previous Date Qty],
        ISNULL((SELECT [Above 25 Days Outstanding] FROM Outstanding WHERE Outstanding.[Team Name] = ST.[Team Name] AND Outstanding.[Sales Person] = ST.[Sales Person]), 0) AS [Above 25 Days Outstanding],
        ISNULL((SELECT [Target Customer Count] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS [Target Customer Count],
        ISNULL((SELECT [Target Customer Reached] FROM CustomerReached WHERE CustomerReached.[Team Name] = ST.[Team Name] AND CustomerReached.[Sales Person] = ST.[Sales Person]), 0) AS [Target Customer Reached]
    FROM SalesTeamCTE ST
    {sub_query}
    ORDER BY ST.[Team Name], ST.[Sales Person];
    """
    return sql_query


def welding_electrode_product_sales_query(start_date, end_date, team_names):
    if team_names:
        sub_query = f"WHERE [Team Name] in ({team_names})"
    sql_query = f"""
    WITH 
    --TargetCustomers
    TargetCustomers AS (
        SELECT     
            SV.[Team Name],  
            SV.[Sales Person],
            ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10,2))),2) AS [Target Qty]
        FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)   
        WHERE [Item Category] = 'Welding Electrodes'
        GROUP BY 
            SV.[Team Name],
            SV.[Sales Person]
    ),
    --Sales 
    Sales AS (
        SELECT          
            ST.[Team Name],   
            ST.[Sales Person],
            TC.[Target Qty], -- Corrected to use Target Qty from TargetCustomers
            SUM(CASE WHEN SV.[Item Details] = 'Welding Electrodes' THEN [Qty(Box)] END) AS [Achv Qty]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)  
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK) 
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))  
        INNER JOIN TargetCustomers TC -- Joining with TargetCustomers to get Target Qty
            ON TC.[Team Name] = ST.[Team Name]
            AND TC.[Sales Person] = ST.[Sales Person]
        WHERE SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}' 
        AND SV.[Item Details] = 'Welding Electrodes' 
        GROUP BY 
            ST.[Team Name], 
            ST.[Sales Person],
            TC.[Target Qty] -- Grouping by Target Qty to get correct sum
    ),
    --Final Sales Report
    SalesReportFinal AS (
        SELECT 
            [Team Name],  
            [Sales Person],
            [Target Qty],
            SUM([Achv Qty]) AS [Achv Qty]
        FROM (
            SELECT 
                [Team Name], 
                [Sales Person],
                [Target Qty], 
                SUM([Achv Qty]) AS [Achv Qty]
            FROM Sales
            GROUP BY 
                [Team Name], 
                [Sales Person],
                [Target Qty]

            UNION ALL

            SELECT          
                TC.[Team Name],   
                TC.[Sales Person],
                TC.[Target Qty], 
                CAST(0 AS DECIMAL(10,2)) AS [Achv Qty]
            FROM TargetCustomers TC
            INNER JOIN (
                SELECT DISTINCT [Team Name], [Sales Person] FROM TargetCustomers
                EXCEPT
                SELECT DISTINCT [Team Name], [Sales Person] FROM Sales
            ) ah
            ON ah.[Team Name] = TC.[Team Name] AND ah.[Sales Person] = TC.[Sales Person]
        ) ap
        GROUP BY
            [Team Name],   
            [Sales Person],
            [Target Qty]
    )
    --Query to retrieve final results with achieved percentage and ordered by team name
    SELECT    
        [Team Name],    
        [Sales Person],
        [Target Qty],
        [Achv Qty],
        CASE 
            WHEN [Target Qty] > 0 THEN ROUND(([Achv Qty] / [Target Qty]) * 100, 2)
            ELSE 0
        END AS [Achieved %]
    FROM SalesReportFinal
    {sub_query}
    ORDER BY [Team Name];

    """
    return sql_query

def durastrong_tmt_product_sales_query(start_date, end_date, team_names):
    if team_names:
        sub_query = f"WHERE [Team Name] in ({team_names})"
    sql_query = f"""
    WITH TempSalesTeam AS (
        SELECT DISTINCT  
            ST.[Team Name],   
            [Sales Person], 
            CAST(0 AS DECIMAL(10, 2)) AS [Target Qty],
            CAST(0 AS DECIMAL(10, 2)) AS [Sales Achv] 
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
    ),
    TargetCustomers AS (
        SELECT  
            SV.[Team Name],   
            SV.[Sales Person], 
            ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10, 2))), 2) AS [Target Qty] 
        FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)
        WHERE [Item Category] = 'DURASTRONG TMT' 
        AND [Item Category] <> 'Welding Electrodes'
        GROUP BY 
            SV.[Team Name], 
            SV.[Sales Person]
    ),
    CTESales AS (
        SELECT      
            ST.[Team Name],
            ST.[Sales Person],  
            SUM([Qty(MTs)]) AS [Sales Achv]
        FROM TempSalesTeam ST WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK) 
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        WHERE SV.[Item Details] = 'DURASTRONG TMT'
        AND SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY 
            ST.[Team Name],
            ST.[Sales Person]
    ),
    TempSales AS (
        SELECT 
            [Team Name],
            [Sales Person],
            SUM([Sales Achv]) AS [Sales Achv] 
        FROM CTESales
        GROUP BY 
            [Team Name],
            [Sales Person]
    ),
    FinalSalesTeam AS (
        SELECT 
            ST.[Team Name],
            ST.[Sales Person], 
            ISNULL(TC.[Target Qty], 0) AS [Target Qty],
            ISNULL(TS.[Sales Achv], 0) AS [Sales Achv]
        FROM TempSalesTeam ST
        LEFT JOIN TargetCustomers TC ON TC.[Team Name] = ST.[Team Name]
            AND TC.[Sales Person] = ST.[Sales Person]
        LEFT JOIN TempSales TS ON TS.[Team Name] = ST.[Team Name]
            AND TS.[Sales Person] = ST.[Sales Person]
    )
    SELECT DISTINCT 
        [Team Name],
        [Sales Person],
        [Target Qty],
        [Sales Achv],
        ISNULL(ROUND(CAST([Sales Achv] AS FLOAT) / NULLIF(CAST([Target Qty] AS FLOAT), 0) * 100, 0), 0) AS [Achv %]
    FROM FinalSalesTeam
    {sub_query}
    ORDER BY [Team Name];
    """
    return sql_query

def sales_register_query(start_date, end_date, team_names = None):
    if team_names:
        sub_query = f"AND t.[Team Name] IN  ({team_names})"
    sql_query = f"""
    SELECT
        v.*,
        t.[Team Name]
    FROM
        tbl_SalesVouchers v
    JOIN
        tbl_SalesTeam t ON v.[Sales Person -2] = t.[Sales Person]
    WHERE
        v.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
    {sub_query}
    """
    return sql_query

def block_customers_list_query(team_names = None):
    if team_names:
        sub_query = f"AND t.[Team Name] IN ({team_names})"
    sql_query = f"""
    SELECT
        c.*,
        t.[Team Name]
    FROM
        tbl_CustomerList c
    JOIN
        tbl_SalesTeam t ON c.[Sales Person] = t.[Sales Person]
    WHERE
        LOWER(c.[Ledger Status]) LIKE '%inactive%'
    {sub_query}
    """
    return sql_query


def all_customers_sales_query(start_date, end_date, user, team_names, salesman = None):
    if is_salesman(user):
        full_name = user.full_name
        sub_query = f"AND (LOWER(t.[Sales Person]) = LOWER('{full_name}'))"
    elif is_manager(user):
        sub_query = f"AND t.[Team Name] in ({team_names})"
        if salesman:
            sub_query += f"AND (LOWER(t.[Sales Person]) = LOWER('{salesman}'))"
    else:
        sub_query = ''

    sql_query = f"""
    SELECT 
        v.[Customer Name],
        v.[Sales Person -2] AS salesman_name,
        t.[Team Name],
        SUM(COALESCE(v.[Qty(MTs)], 0)) AS achvd_qty
    FROM 
        tbl_SalesVouchers v
    JOIN 
        tbl_SalesTeam t ON v.[Sales Person -2] = t.[Sales Person]
    WHERE 
        v.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
        {sub_query}
    GROUP BY 
        v.[Customer Name],
        v.[Sales Person -2],
        t.[Team Name]
    ORDER BY 
        v.[Customer Name],
        v.[Sales Person -2]
    """
    return sql_query


def product_wise_month_on_month_query(start_date, end_date, user, team_names, salesman=None):
    if is_salesman(user):
        full_name = user.full_name
        sub_query = f"AND ST.[Sales Person] = '{full_name}'"
    elif is_manager(user):
        sub_query = f"AND ST.[Team Name] in ({team_names})"
        if salesman:
            sub_query += f"AND (LOWER(ST.[Sales Person]) = LOWER('{salesman}'))"
    else:
        sub_query = ''
    sql_query = f"""
    WITH Sales AS (
    SELECT          
        IL.[Item Category] AS [Item Category],
        SUM(CASE WHEN SV.[Item Details] <> 'Welding Electrodes' THEN [Qty(MTs)] ELSE 0 END) AS [Achv Qty] 
    FROM (SELECT DISTINCT
            [Item Details],
            [Item Category] 
            FROM dbo.tbl_ItemsList IL  WITH(NOLOCK)) IL   
    INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(NOLOCK) 
        ON IL.[Item Details] = SV.[Item Details]
    INNER JOIN [dbo].[tbl_SalesTeam] ST WITH(NOLOCK)
        ON SV.[Sales Person -2] = ST.[Sales Person]  
    WHERE SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'  
        AND SV.[Item Details] <> 'Welding Electrodes'
        {sub_query}
    GROUP BY IL.[Item Category]
    )
    SELECT 
        S.[Item Category] AS [item_category],
        S.[Achv Qty] AS [achvd_qty]
    FROM Sales S
    ORDER BY S.[Item Category];
    """

    return sql_query

def review_product_wise_query(month_count, team_names, salesman=None):
    sub_query, sub_query2, sub_query3 = ["", "", ""]
    if team_names:
        sub_query = f"WHERE [Team Name] in ({team_names})"
        if salesman:
            sub_query2 = f"AND (LOWER(ST.[Sales Person]) = LOWER('{salesman}'))"
            sub_query3 = f"AND (LOWER(SV.[Sales Person]) = LOWER('{salesman}'))"
    sql_query = f"""
    WITH TargetCustomers AS (
        SELECT 
            SV.[Team Name],  
            SV.[Item Category] AS [Product cluster], 
            ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10,2))), 2) AS [Target Qty]
        FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)
        WHERE SV.[Item Category] <> 'Welding Electrodes'
        {sub_query3}
        GROUP BY 
            SV.[Team Name],
            SV.[Item Category]
    ),
    SalesTemp AS (
        SELECT
            ST.[Team Name],   
            IL.[Item Category] AS [Product cluster],
            DATEPART(YEAR, SV.[Voucher Date]) AS [Year],
            CASE 
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 1 THEN 'January'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 2 THEN 'February'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 3 THEN 'March'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 4 THEN 'April'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 5 THEN 'May'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 6 THEN 'June'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 7 THEN 'July'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 8 THEN 'August'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 9 THEN 'September'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 10 THEN 'October'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 11 THEN 'November'
                WHEN DATEPART(MONTH, SV.[Voucher Date]) = 12 THEN 'December'
                ELSE ''
            END AS [Month],
            SUM(CASE WHEN SV.[Item Details] <> 'Welding Electrodes' THEN SV.[Qty(MTs)] ELSE 0 END) AS [Achv Qty]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        INNER JOIN (
            SELECT DISTINCT
                [Item Details],
                [Item Category]
            FROM dbo.tbl_ItemsList IL WITH (NOLOCK)
        ) IL ON IL.[Item Details] = SV.[Item Details]
        WHERE SV.[Voucher Date] >= DATEADD(MONTH, -{month_count}, GETDATE())
        {sub_query2}
        AND SV.[Item Details] <> 'Welding Electrodes'
        GROUP BY
            ST.[Team Name], 
            IL.[Item Category],
            DATEPART(YEAR, SV.[Voucher Date]),
            DATEPART(MONTH, SV.[Voucher Date])
    ),
    CombinedSales AS (
        SELECT 
            COALESCE(TC.[Team Name], ST.[Team Name]) AS [Team Name],   
            COALESCE(TC.[Product cluster], ST.[Product cluster]) AS [Product cluster],
            COALESCE(TC.[Target Qty], 0) AS [Target Qty], 
            COALESCE(ST.[Year], 0) AS [Year],
            COALESCE(ST.[Month], '') AS [Month],
            COALESCE(SUM(ST.[Achv Qty]), 0) AS [Achv Qty]
        FROM TargetCustomers TC
        FULL JOIN SalesTemp ST
            ON TC.[Team Name] = ST.[Team Name] 
            AND TC.[Product cluster] = ST.[Product cluster]
        GROUP BY
            COALESCE(TC.[Team Name], ST.[Team Name]),   
            COALESCE(TC.[Product cluster], ST.[Product cluster]),
            COALESCE(TC.[Target Qty], 0),
            COALESCE(ST.[Year], 0),
            COALESCE(ST.[Month], '')
    )

    -- Final output
    SELECT    
        [Team Name],    
        [Product cluster],
        [Target Qty],
        [Achv Qty],
        [Year],
        [Month]
    FROM CombinedSales
    {sub_query}
    ORDER BY [Team Name], [Product cluster], [Year], [Month];
    """

    return sql_query

def target_customers_sales_query(start_date, end_date, user, team_names, salesman = None):
    if is_salesman(user):
        full_name = user.full_name
        sub_query = f"WHERE (LOWER(ST.[Sales Person]) = LOWER('{full_name}'))"
    elif is_manager(user):
        sub_query = f"WHERE ST.[Team Name] in ({team_names})"
        if salesman:
            sub_query += f"AND (LOWER(ST.[Sales Person]) = LOWER('{salesman}'))"
    else:
        sub_query = ''

    sql_query = f"""
    WITH SalesTeamCTE AS (
        SELECT   
            ST.[Team Name],   
            [Sales Person],
            CAST(0 AS DECIMAL(10,2)) AS [Target Qty],  
            CAST(0 AS DECIMAL(10,2)) AS [Achv Qty],
            CAST(GETDATE()-2 AS DATE) AS [Previous Date]
        FROM [dbo].[tbl_SalesTeam] ST WITH(NOLOCK)  
    )
    , TargetCustomers AS (
        SELECT DISTINCT  
            SV.[Team Name],    
            [Sales Person],  
            SV.[Customer Name],
            ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10,2))),2) AS [Target Qty], 
            SV.[Date] 
        FROM [dbo].[tbl_TargetCustomers] SV WITH(NOLOCK)   
        WHERE [Item Category] <> 'Welding Electrodes'
        GROUP BY 
            SV.[Team Name],
            [Sales Person],  
            SV.[Customer Name],  
            SV.[Date] 
    )
    , Sales AS (
        SELECT      
            ST.[Team Name],   
            [Sales Person],
            SV.[Customer Name],
            SUM([Qty(MTs)]) AS [Achv Qty], 
            ST.[Previous Date] 
        FROM SalesTeamCTE ST 
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(NOLOCK) 
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person])) 
            AND SV.[Item Details] <> 'Welding Electrodes'
            AND SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}' -- Filter by date range
        GROUP BY 
            ST.[Team Name],    
            [Sales Person],
            SV.[Customer Name],
            ST.[Previous Date]
    )
    SELECT DISTINCT 
        TC.[Customer Name],
        ISNULL(TC.[Target Qty], 0) AS [Target Qty],
        ISNULL(S.[Achv Qty], 0) AS [Achv Qty]
    FROM SalesTeamCTE ST
    INNER JOIN TargetCustomers TC 
        ON TC.[Team Name] = ST.[Team Name] AND TC.[Sales Person] = ST.[Sales Person]
    LEFT JOIN Sales S 
        ON S.[Team Name] = ST.[Team Name] AND S.[Sales Person] = ST.[Sales Person] AND S.[Customer Name] = TC.[Customer Name]
    {sub_query}
    ORDER BY TC.[Customer Name];
    """
    return sql_query

def review_salesman_wise_query1(team_names, salesman = None):

    if team_names:
        sub_query = f"WHERE ST.[Team Name] in ({team_names})"
        if salesman:
            sub_query += f"AND (LOWER(ST.[Sales Person]) = LOWER('{salesman}'))"

    sql_query = f"""
    WITH SalesTeamCTE AS (
        SELECT   
            ST.[Team Name],   
            ST.[Sales Person],
            CAST(GETDATE() AS DATE) AS [Date],
            CAST(0 AS DECIMAL(10, 2)) AS [Target Qty],  
            CAST(0 AS DECIMAL(10, 2)) AS [Achv Qty],
            CAST(GETDATE() - 2 AS DATE) AS [Previous Date]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
        GROUP BY ST.[Team Name], ST.[Sales Person]
    ),
    TargetCustomers AS (
        SELECT  
            TC.[Team Name],    
            TC.[Sales Person],
            ROUND(SUM(CAST(TC.[Target Qty] AS DECIMAL(10, 2))), 2) AS [Target Qty], 
            COUNT(DISTINCT TC.[Customer ID]) AS [Target Customer Count]
        FROM [dbo].[tbl_TargetCustomers] TC WITH (NOLOCK)
        WHERE TC.[Item Category] <> 'Welding Electrodes'
        GROUP BY 
            TC.[Team Name], TC.[Sales Person]
    ),
    Sales AS (
        SELECT      
            TC.[Team Name],
            TC.[Sales Person],
            SUM(SV.[Qty(MTs)]) AS [Achv Qty]
        FROM [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_TargetCustomers] TC WITH (NOLOCK)
            ON SV.[Customer ID] = TC.[Customer ID]
        WHERE SV.[Item Details] <> 'Welding Electrodes'
        AND YEAR(SV.[Voucher Date]) = YEAR(GETDATE()) 
            AND MONTH(SV.[Voucher Date]) = MONTH(GETDATE())
        GROUP BY 
            TC.[Team Name], TC.[Sales Person]
    ),
    CustomerReached AS (
        SELECT      
            TC.[Team Name],
            TC.[Sales Person],
            COUNT(DISTINCT CASE WHEN [Qty(MTs)] > 0 THEN SV.[Customer ID] ELSE NULL END) AS [Target Customer Reached]
        FROM [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_TargetCustomers] TC WITH (NOLOCK)
            ON SV.[Customer ID] = TC.[Customer ID]
        WHERE SV.[Item Details] <> 'Welding Electrodes'
        AND YEAR(SV.[Voucher Date]) = YEAR(GETDATE()) 
            AND MONTH(SV.[Voucher Date]) = MONTH(GETDATE())
        GROUP BY 
            TC.[Team Name], TC.[Sales Person]
    ),
    Outstanding AS (
        SELECT  
            ST.[Team Name],
            OS.[Sales Person -2] AS [Sales Person],
            SUM(CASE WHEN OS.Ageing > 25 THEN OS.[Pending Amount] ELSE 0 END) AS [Above 25 Days Outstanding]
        FROM [dbo].[tbl_OutStandings] OS WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
            ON LTRIM(RTRIM(OS.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        WHERE 
            CAST(OS.[Created Date] AS DATE) = (
                SELECT MAX(CAST([Created Date] AS DATE)) 
                FROM [dbo].[tbl_OutStandings] OS2
            )
        GROUP BY 
            ST.[Team Name],
            OS.[Sales Person -2]
    )
    SELECT DISTINCT 
        ST.[Team Name],
        ST.[Sales Person],
        ISNULL(TC.[Target Qty], 0) AS [Target Qty],  
        ISNULL(OS.[Above 25 Days Outstanding], 0) AS [Above 25 Days Outstanding],
        ISNULL(TC.[Target Customer Count], 0) AS [Target Customer Count],
        ISNULL(CR.[Target Customer Reached], 0) AS [Target Customer Reached]
    FROM SalesTeamCTE ST
    LEFT JOIN TargetCustomers TC ON ST.[Team Name] = TC.[Team Name] AND ST.[Sales Person] = TC.[Sales Person]
    LEFT JOIN Outstanding OS ON ST.[Team Name] = OS.[Team Name] AND ST.[Sales Person] = OS.[Sales Person]
    LEFT JOIN CustomerReached CR ON ST.[Team Name] = CR.[Team Name] AND ST.[Sales Person] = CR.[Sales Person]
    {sub_query}
    ORDER BY ST.[Team Name], ST.[Sales Person];
    """
    return sql_query

def review_salesman_wise_query2(start_date = None, end_date = None, team_names = None):
    if team_names:
        sub_query = f"WHERE ST.[Team Name] in ({team_names})"
    sql_query = f"""
    SELECT
        ST.[Team Name],
        ST.[Sales Person],
        ISNULL(SUM(ISNULL(SV.[Qty(MTs)], 0)), 0) AS [Achv Qty]
    FROM
        [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
    LEFT JOIN
        [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
    ON
        LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        AND SV.[Item Details] <> 'Welding Electrodes'
        AND SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'  -- Adjust dates as per your requirement
    {sub_query}
    GROUP BY
        ST.[Team Name],
        ST.[Sales Person]
    ORDER BY
        ST.[Team Name];


    """
    return sql_query

def get_team_names(manager_name = None):
    sub_query = ''
    if manager_name:
        sub_query = f" WHERE LOWER(ST.[Reporting Manager Name]) = '{manager_name}'"
    sql_query = f"""
    SELECT DISTINCT
        [Team Name]
    FROM
        [dbo].[tbl_HierarchyMapping] ST WITH (NOLOCK)
    {sub_query}
    """
    return sql_query

def manager_names_query():
    sql_query = "select Distinct [Reporting Manager Name] from tbl_HierarchyMapping"
    return sql_query

def salesman_names_query(team_name = None):
    sub_query = ""
    if team_name:
        sub_query = f"WHERE [Team Name] = '{team_name}'"
    sql_query = f"Select Distinct [Sales Person] from tbl_HierarchyMapping {sub_query}"
    return sql_query

class InsentiveQueries:
    def __init__(self, month, year, salesman = None) -> None:
        self.month = month
        self.year = year
        self.salesman = salesman

    def elegibilty_criteria(self):
        sql_query = f"""
        WITH SalesTeamCTE AS (
        SELECT   
                ST.[Team Name],   
                [Sales Person], 
                CAST(GETDATE() AS Date) AS [Date],
                CAST(0 AS Decimal(10,2)) AS [Target Qty],  
                CAST(0 AS Decimal(10,2)) AS [Achv Qty],
                CAST(GETDATE()-2 AS Date) AS [Previous Date]
        FROM [dbo].[tbl_SalesTeam] ST WITH(NOLOCK)
        ),
        TargetCustomers AS (
        SELECT DISTINCT
                SV.[Team Name],    
                [Sales Person],
                ROUND(SUM(CAST(SV.[Target Qty] AS Decimal(10,2))),2) AS [Target Qty]
        FROM [dbo].[tbl_TargetCustomers] SV WITH(NOLOCK)
        WHERE [Item Category] <> 'Welding Electrodes'
        GROUP BY 
                SV.[Team Name],
                [Sales Person]
        ),
        Sales AS (
        SELECT      
                ST.[Team Name],   
                [Sales Person],
                SUM([Qty(MTs)]) AS [Achv Qty]
        FROM SalesTeamCTE ST
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(NOLOCK)
        ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        AND SV.[Item Details] <> 'Welding Electrodes'
        AND YEAR(SV.[Voucher Date]) = {self.year} 
        AND MONTH(SV.[Voucher Date]) = {self.month}
        GROUP BY 
                ST.[Team Name],    
                [Sales Person]
        ),
        FilteredSales AS (
        SELECT DISTINCT
            S.[Team Name],
            S.[Sales Person],
            SV.[Voucher No],
            CASE 
                WHEN DATEDIFF(DAY, SV.[Voucher Date], RR.[Receipt Date]) <= 35 
                    --  AND NOT EXISTS (
                    --      SELECT 1
                    --      FROM [dbo].[tbl_OutStandings] OS WITH (NOLOCK)
                    --      WHERE OS.[Bill No] = SV.[Voucher No]
                    --  )
                    THEN 1 
                ELSE 0 
            END AS [Condition Met]
        FROM Sales S
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(NOLOCK) ON S.[Sales Person] = SV.[Sales Person -2]
        INNER JOIN [dbo].[tbl_ReceiptRegister] RR WITH(NOLOCK) ON RR.[Invoice No] = SV.[Voucher No]
        WHERE YEAR(SV.[Voucher Date]) = {self.year} 
            AND MONTH(SV.[Voucher Date]) = {self.month}
            AND DATEDIFF(DAY, SV.[Voucher Date], RR.[Receipt Date]) <= 35
        GROUP BY 
            S.[Team Name],
            S.[Sales Person],
            SV.[Voucher No],
            SV.[Voucher Date],
            RR.[Receipt Date]
        )

        SELECT DISTINCT
        ST.[Team Name],
        ST.[Sales Person],
        ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS [Target Qty],
        ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS [Achv Qty],
        ISNULL(ROUND(CAST(ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS float) / NULLIF(CAST(ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS float), 0) * 100, 0), 0) AS [Achv %],
        FS.[Condition Met] AS [Condition Met]
        FROM SalesTeamCTE ST
        LEFT JOIN FilteredSales FS
        ON ST.[Team Name] = FS.[Team Name] AND ST.[Sales Person] = FS.[Sales Person]
        WHERE ST.[Sales Person] = '{self.salesman}'

        AND ISNULL(ROUND(CAST(ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS float) / NULLIF(CAST(ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS float), 0) * 100, 0), 0) > 80
        ORDER BY ST.[Team Name], ST.[Sales Person];
        """
        return sql_query
    
    def incentive_amount_query(self):
        sql_query = f"""
WITH Sales AS (
    SELECT          
        ST.[Sales Person],
        IL.[Item Category] AS [Product cluster],
        IL.[Item Details] AS [Product Details], -- Added Product Details field
        ISNULL(TC.[Target Qty], 0) AS [Target Qty],
        SUM(CASE WHEN SV.[Item Details] <> 'Welding Electrodes' THEN [Qty(MTs)] ELSE 0 END) AS [Achv Qty]
    FROM [dbo].[tbl_SalesTeam] ST WITH(NOLOCK)  
    INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(NOLOCK) 
        ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))  
    INNER JOIN (
        SELECT DISTINCT
            [Item Details],
            [Item Category] 
        FROM dbo.tbl_ItemsList IL WITH(NOLOCK)
    ) IL   
        ON IL.[Item Details] = SV.[Item Details]  
    LEFT JOIN (
        SELECT     
            [Sales Person],
            [Item Category] AS [Product cluster],
            ROUND(SUM(CAST([Target Qty] AS DECIMAL(10,2))),2) AS [Target Qty]
        FROM [dbo].[tbl_TargetCustomers] WITH(NOLOCK)
        GROUP BY 
            [Sales Person],
            [Item Category]
    ) TC 
        ON TC.[Sales Person] = ST.[Sales Person] AND TC.[Product cluster] = IL.[Item Category]
    WHERE YEAR(SV.[Voucher Date]) = {self.year} AND MONTH(SV.[Voucher Date]) = {self.month}
    AND (LOWER(ST.[Sales Person]) = LOWER('{self.salesman}'))
    GROUP BY 
        ST.[Sales Person],
        IL.[Item Category],
        IL.[Item Details], -- Added for Product Details
        TC.[Target Qty]
)
SELECT    
    [Sales Person],
    [Product cluster],
    [Product Details], -- Include Product Details in the SELECT list
    [Target Qty],
    SUM([Achv Qty]) AS [Achv Qty],
    ISNULL(ROUND(SUM([Achv Qty]) / NULLIF([Target Qty], 0) * 100, 0), 0) AS [Achv %]
FROM Sales
GROUP BY
    [Sales Person],
    [Product cluster],
    [Product Details], -- Group by Product Details as well
    [Target Qty];

        """
        return sql_query