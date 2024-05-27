def sales_summary_query(start_date, end_date, pre_date):
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


def sales_collection_outstanding_summary(start_date, end_date, pre_date):
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
        WHERE ST.[Team Name] IS NOT NULL
        ORDER BY ST.[Team Name], ST.[Sales Person];
    """
    return sql_query


def product_wise_sales_summary_query(start_date, end_date, pre_date):
    sql_query = f"""
    WITH TargetCustomers AS (
      SELECT   
        [Item Category],
        ROUND(SUM(CAST([Target Qty] AS Decimal(10,2))), 2) AS [Target Qty]
      FROM [dbo].[tbl_TargetCustomers] WITH (NOLOCK)   
      WHERE [Item Category] <> 'Welding Electrodes'
      GROUP BY [Item Category]
    ),
    Sales AS (
      SELECT          
        IL.[Item Category] as [Item Category],
        CAST(0 AS Decimal(10,2)) AS [Target Qty],
        SUM(CASE WHEN SV.[Item Details] <> 'Welding Electrodes' THEN [Qty(MTs)] ELSE 0 END) AS [Achv Qty] 
      FROM (SELECT DISTINCT
              [Item Details],
              [Item Category] 
            FROM dbo.tbl_ItemsList IL  WITH(Nolock)) IL   
      INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(Nolock) 
        ON IL.[Item Details] = SV.[Item Details]  
      Where SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'  
        AND SV.[Item Details] <> 'Welding Electrodes' 
      GROUP BY IL.[Item Category]
    ),
    PreviousDateQty AS (
      SELECT          
        IL.[Item Category] as [Item Category],
        CAST(0 AS Decimal(10,2)) AS [Target Qty],
        SUM(CASE WHEN SV.[Item Details] <> 'Welding Electrodes' THEN [Qty(MTs)] ELSE 0 END) AS [Achv Qty] 
      FROM (SELECT DISTINCT
              [Item Details],
              [Item Category] 
            FROM dbo.tbl_ItemsList IL  WITH(Nolock)) IL   
      INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(Nolock) 
        ON IL.[Item Details] = SV.[Item Details]  
      WHERE 
        CAST(SV.[Voucher Date] AS DATE) = '{pre_date}'
        AND SV.[Item Details] <> 'Welding Electrodes' 
      GROUP BY IL.[Item Category]
    )
    SELECT 
      TC.[Item Category],
      TC.[Target Qty],
      S.[Achv Qty],
      PDQ.[Achv Qty] AS [Pre Day Sales],
      CASE 
        WHEN TC.[Target Qty] = 0 THEN 0
        ELSE (S.[Achv Qty] / TC.[Target Qty]) * 100 
      END AS [Achievement Percentage]
    FROM TargetCustomers TC
    LEFT JOIN Sales S ON TC.[Item Category] = S.[Item Category]
    LEFT JOIN PreviousDateQty PDQ ON TC.[Item Category] = PDQ.[Item Category]
    ORDER BY TC.[Item Category];
    """
    return sql_query

def weekly_report_query(start_date, end_date):
    sql_query = """
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
            COALESCE(WS.[Weekly Achvd Qty], 0) AS [Weekly Achved Qty(MTs)]
           
        FROM SalesTeam ST
        LEFT JOIN TargetCustomers TC ON ST.[Sales Person] = TC.[Sales Person]
        LEFT JOIN Sales S ON ST.[Sales Person] = S.[Sales Person] AND ST.[Team Name] = S.[Team Name]
        LEFT JOIN CollectionAmount CA ON ST.[Sales Person] = CA.[Sales Person]
        LEFT JOIN Outstandings O ON ST.[Sales Person] = O.[Sales Person]
        LEFT JOIN WeeklySales WS ON ST.[Sales Person] = WS.[Sales Person] AND ST.[Team Name] = WS.[Team Name]

        WHERE ST.[Team Name] IS NOT NULL
        ORDER BY 1;

        """
    return sql_query

def collection_report_by_date_range(date):

    sql_query = f"""
        SELECT st.[Team Name],
            st.[Sales Person],
        SUM(rr.[Credit Amount]) AS TotalCreditAmount
        FROM tbl_SalesTeam st
        JOIN tbl_ReceiptRegister rr ON st.[Sales Person] = rr.[Sales Person -2]
        WHERE rr.[Receipt Date] = '{date}'
        GROUP BY st.[Team Name],
        st.[Sales Person]
        ORDER by 1;
    """
    return sql_query


def customer_wise_outstanding_query(outstanding_value):
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


def cr_utilization_report_query():
        sql_query = """
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
            GROUP BY 
                t1."Team Name", t1."Sales Person", t1."Customer Name", t1."Customer ID", SUM_OUTSTANDING.[All Outstanding] -- Include "All Outstanding" in the GROUP BY clause
            ORDER BY 
                t1."Team Name", t1."Sales Person", t1."Customer Name", t1."Customer ID";

            """
        return sql_query


def team_and_product_wise_query():
    sql_query = """
    WITH TargetCustomers AS (
        SELECT 
            SV.[Team Name],  
            SV.[Item Category] AS [Product cluster], 
            ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10,2))), 2) AS [Target Qty]
        FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)
        WHERE SV.[Item Category] <> 'Welding Electrodes'
        GROUP BY 
            SV.[Team Name],
            SV.[Item Category]
    ),
    SalesTemp AS (
        SELECT
            ST.[Team Name],   
            IL.[Item Category] AS [Product cluster],
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
        WHERE YEAR(SV.[Voucher Date]) = YEAR(GETDATE())
        AND MONTH(SV.[Voucher Date]) = MONTH(GETDATE())
        AND SV.[Item Details] <> 'Welding Electrodes'
        GROUP BY
            ST.[Team Name], 
            IL.[Item Category]
    ),
    CombinedSales AS (
        SELECT 
            COALESCE(TC.[Team Name], ST.[Team Name]) AS [Team Name],   
            COALESCE(TC.[Product cluster], ST.[Product cluster]) AS [Product cluster],
            COALESCE(TC.[Target Qty], 0) AS [Target Qty], 
            SUM(ST.[Achv Qty]) AS [Achv Qty]
        FROM TargetCustomers TC
        FULL JOIN SalesTemp ST
            ON TC.[Team Name] = ST.[Team Name] 
            AND TC.[Product cluster] = ST.[Product cluster]
        GROUP BY
            COALESCE(TC.[Team Name], ST.[Team Name]),   
            COALESCE(TC.[Product cluster], ST.[Product cluster]),
            COALESCE(TC.[Target Qty], 0)
    )

    -- Final output
    SELECT    
        [Team Name],    
        [Product cluster],
        [Target Qty],
        [Achv Qty],
        ROUND(CAST([Achv Qty] AS FLOAT) / NULLIF(CAST([Target Qty] AS FLOAT), 0) * 100, 0) AS [Achv %]
    FROM CombinedSales
    ORDER BY [Team Name], [Product cluster];

    """
    return sql_query


def salesman_and_product_wise_query():
    sql_query = """
    WITH Sales AS (
        SELECT          
            ST.[Sales Person],
            IL.[Item Category] AS [Product cluster],
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
            WHERE [Item Category] <> 'Welding Electrodes'
            GROUP BY 
                [Sales Person],
                [Item Category]
        ) TC 
            ON TC.[Sales Person] = ST.[Sales Person] AND TC.[Product cluster] = IL.[Item Category]
        WHERE YEAR(SV.[Voucher Date]) = YEAR(GETDATE()) AND MONTH(SV.[Voucher Date]) = MONTH(GETDATE()) AND SV.[Item Details] <> 'Welding Electrodes' 
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
