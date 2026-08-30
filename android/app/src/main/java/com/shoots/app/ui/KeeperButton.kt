package com.shoots.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.shoots.app.Amber
import com.shoots.app.Hairline
import com.shoots.app.Ink
import com.shoots.app.R
import com.shoots.app.WarmWhite

@Composable
fun KeeperButton(
    kept: Boolean,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    Box(
        Modifier
            .size(44.dp)
            .background(Ink.copy(alpha = 0.88f), CircleShape)
            .border(1.dp, if (kept) Amber.copy(alpha = 0.75f) else Hairline, CircleShape)
            .semantics {
                contentDescription = if (kept) "Remove Keeper mark" else "Mark as Keeper"
            }
            .clickable(
                enabled = enabled,
                role = Role.Button,
                onClickLabel = if (kept) "Remove Keeper mark" else "Mark as Keeper",
                onClick = onClick,
            ),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_bookmark),
            contentDescription = null,
            tint = if (kept) Amber else WarmWhite,
            modifier = Modifier.size(20.dp),
        )
    }
}
