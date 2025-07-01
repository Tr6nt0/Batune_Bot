## Using BatuneBot

### For Everyone
- **Add a fortune**  
  `mika add Your fortune text here`  
  - In any server or DMs
  - Submissions require admin approval
  - No ID assigned until approved

### For Admins
- **Approve submissions**  
  `mika approve <id>` - Approve a pending submission
- **Reject submissions**  
  `mika reject <id>` - Reject a submission
- **View submissions**  
  `mika submissions` - Show recent submissions
- **View fortunes**  
  `mika fortunes` - Show recently approved fortunes
- **Test posting**  
  `mika test` - Post today's fortune immediately
- **Reset fortunes**  
  `mika reset` - Mark all fortunes as unused

### ID System
- **Global Fortunes**:
  - Original Batune: Keep original IDs (1-799)
  - Approved user submissions: Start at 800
  - Format: `Global-800`
  
- **Guild Fortunes**:
  - Guild-specific sequence restarts at 1 per guild
  - Format: `Guild-<GuildID>-<Sequence>`
  - Example: `Guild-123456789-1`

### Approval Workflow
1. User submits fortune
2. Admin reviews with `mika submissions`
3. Admin approves/rejects
4. Approved fortunes get IDs and enter queue
5. Guild fortunes have priority, then global in order
