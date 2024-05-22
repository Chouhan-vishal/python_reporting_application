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
    query = f"""
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
                SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
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
    return query
